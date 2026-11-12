from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from docx import Document
from pypdf import PdfReader

from app import (
    APIError,
    _compress_image_pdf,
    _compress_text_safe,
    _create_document_docx,
    _create_document_pdf,
    _pdf_interactive_content,
    create_app,
    generate_caption,
    generate_document,
)


class BoringstuffAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = str(Path(self.temporary_directory.name) / "test.sqlite3")
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": database_path,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_writing_tools_requires_gemini_and_returns_ai_result(self) -> None:
        response = self.client.post("/api/writing-tools", json={"action": "rewrite", "text": "hello"})
        self.assertEqual(503, response.status_code)
        self.assertEqual("ai_not_configured", response.get_json()["code"])

        self.app.config["GEMINI_API_KEY"] = "test-key"
        with patch("app._gemini_text", return_value="Hello there.") as generate:
            response = self.client.post(
                "/api/writing-tools",
                json={"action": "rewrite", "text": "hello", "tone": "friendly", "language": "en"},
            )
        self.assertEqual(200, response.status_code)
        self.assertEqual("Hello there.", response.get_json()["result"])
        self.assertTrue(response.get_json()["aiGenerated"])
        self.assertEqual("Gemini", response.get_json()["provider"])
        self.assertIn("untrusted data", generate.call_args.args[0])

    def test_writing_tools_rejects_unsupported_action_and_oversized_text(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key"
        response = self.client.post("/api/writing-tools", json={"action": "invent", "text": "hello"})
        self.assertEqual(400, response.status_code)
        response = self.client.post("/api/writing-tools", json={"action": "rewrite", "text": "x" * 12001})
        self.assertEqual(400, response.status_code)

    def test_document_generator_validates_and_formats_resignation(self) -> None:
        content, title, fields = generate_document(
            {
                "type": "resignation",
                "fullName": "Ada Lovelace",
                "jobTitle": "Engineer",
                "companyName": "Analytical Engines",
                "recipientName": "Grace Hopper",
                "email": "ada@example.com",
                "phone": "+1 555 0100",
                "date": "2026-11-09",
                "reason": "a new opportunity",
                "lastWorkingDay": "2026-11-30",
            }
        )
        self.assertEqual(title, "Resignation letter: Analytical Engines")
        self.assertEqual(fields["fullName"], "Ada Lovelace")
        self.assertIn("November 9, 2026", content)
        self.assertIn("My last working day will be November 30, 2026.", content)
        self.assertIn("ada@example.com | +1 555 0100", content)

    def test_resignation_rejects_line_breaks_in_document_header_fields(self) -> None:
        base_payload = {
            "type": "resignation",
            "fullName": "Ada Lovelace",
            "jobTitle": "Engineer",
            "companyName": "Analytical Engines",
            "date": "2026-11-09",
        }
        for field, value in (
            ("fullName", "Ada Lovelace\nUnauthorized line"),
            ("jobTitle", "Engineer\rInjected title"),
            ("companyName", "Analytical Engines\nAnother company"),
            ("recipientName", "Grace Hopper\nUnexpected recipient"),
        ):
            with self.subTest(field=field):
                payload = {**base_payload, field: value}
                with self.assertRaisesRegex(APIError, "single line"):
                    generate_document(payload)

    def test_document_generator_creates_personalized_cover_letter(self) -> None:
        content, title, _ = generate_document(
            {
                "type": "cover",
                "fullName": "Ada Lovelace",
                "jobTitle": "Engineer",
                "companyName": "Analytical Engines",
                "date": "2026-11-09",
                "coverDetails": "Built reliable data tools for a small research team.",
            }
        )
        self.assertEqual(title, "Cover letter: Analytical Engines")
        self.assertIn("apply for the Engineer position", content)
        self.assertIn("Built reliable data tools", content)

    def test_document_generator_creates_polished_indonesian_resignation_letter(self) -> None:
        content, title, fields = generate_document(
            {
                "type": "resignation",
                "language": "id",
                "fullName": "Sari Putri",
                "jobTitle": "Analis Data",
                "companyName": "Nusantara Labs",
                "date": "2026-11-09",
                "lastWorkingDay": "2026-11-30",
                "reason": "Saya akan melanjutkan studi.",
            }
        )
        self.assertEqual(title, "Surat pengunduran diri: Nusantara Labs")
        self.assertEqual(fields["language"], "id")
        self.assertIn("9 November 2026", content)
        self.assertIn("Hari kerja terakhir saya adalah 30 November 2026.", content)
        self.assertIn("Pertimbangan yang mendasari keputusan ini adalah: Saya akan melanjutkan studi.", content)
        self.assertIn("Hormat saya,", content)
        pdf_bytes = _create_document_pdf(content, fields["type"], fields["language"])
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            self.assertIn("Surat Pengunduran Diri", document[0].get_text())

    def test_document_generator_localizes_indonesian_cover_letter(self) -> None:
        content, title, _ = generate_document(
            {
                "type": "cover",
                "language": "id",
                "fullName": "Sari Putri",
                "jobTitle": "Analis Data",
                "companyName": "Nusantara Labs",
                "date": "2026-11-09",
                "coverDetails": "Membangun dasbor yang mengurangi waktu pelaporan sebesar 30%.",
            }
        )
        self.assertEqual(title, "Surat lamaran: Nusantara Labs")
        self.assertIn("Kepada Yth. Manajer Perekrutan,", content)
        self.assertIn("Perihal: Lamaran Posisi Analis Data", content)
        self.assertIn("Pengalaman relevan saya antara lain:", content)
        self.assertIn("mengurangi waktu pelaporan sebesar 30%", content)

    def test_cover_letter_quality_scenarios(self) -> None:
        scenarios = [
            {
                "name": "fresh graduate",
                "language": "en",
                "jobTitle": "Junior Data Analyst",
                "companyName": "Northstar Analytics",
                "coverDetails": "Completed a final-year project that used Python to clean survey data.",
                "jobDescription": "Python and careful data analysis are useful.",
                "not_invented": "internship",
            },
            {
                "name": "experienced professional",
                "language": "en",
                "jobTitle": "Product Manager",
                "companyName": "Cedar Works",
                "coverDetails": "Led a five-person team and shipped a billing migration.",
                "resumeText": "Managed product roadmaps and coordinated release planning.",
                "jobDescription": "Leadership, project management, and SQL.",
            },
            {
                "name": "career changer",
                "language": "id",
                "jobTitle": "Junior Developer",
                "companyName": "Ruang Digital",
                "coverDetails": "Saya beralih dari pemasaran dan membuat proyek Python untuk portofolio.",
                "resumeText": "Mengelola kampanye media sosial untuk usaha lokal.",
                "jobDescription": "Python, pemasaran, dan kerja tim.",
            },
            {
                "name": "limited experience",
                "language": "en",
                "jobTitle": "Office Assistant",
                "companyName": "Harbor Health",
                "coverDetails": "Completed a short office placement and organized weekly schedules.",
                "jobDescription": "Communication and organization.",
                "not_invented": "five years",
            },
            {
                "name": "technical background",
                "language": "id",
                "jobTitle": "Backend Engineer",
                "companyName": "Awan Teknologi",
                "coverDetails": "Membuat API Flask dan kueri SQL untuk aplikasi inventaris internal.",
                "jobDescription": "Flask, SQL, dan machine learning.",
            },
            {
                "name": "administrative background",
                "language": "en",
                "jobTitle": "Administrative Coordinator",
                "companyName": "Maple & Finch",
                "coverDetails": "Scheduled meetings and reviewed 80 invoices each month.",
                "jobDescription": "Operations, accounting, and stakeholder management.",
            },
            {
                "name": "incomplete optional information",
                "language": "id",
                "jobTitle": "Staf Administrasi",
                "companyName": "Karya Bersama",
                "coverDetails": "Menyusun arsip digital dan membantu menyiapkan laporan mingguan.",
                "jobDescription": "",
            },
            {
                "name": "long job description",
                "language": "en",
                "jobTitle": "Operations Analyst",
                "companyName": "Summit Group",
                "coverDetails": "Created a Python report for the operations team.",
                "jobDescription": (
                    "Python, SQL, analytics, project management, and communication. "
                    * 70
                )[:5000],
            },
            {
                "name": "unrelated skills",
                "language": "en",
                "jobTitle": "Software Engineer",
                "companyName": "Signal Labs",
                "coverDetails": "Volunteered at a community garden and organized weekend events.",
                "jobDescription": "Python, SQL, and machine learning are required.",
                "not_in_output": ("Python", "SQL", "machine learning"),
            },
            {
                "name": "international company",
                "language": "en",
                "jobTitle": "Research Associate",
                "companyName": "Global Water Institute",
                "coverDetails": "Published a university thesis on water quality and managed lab samples.",
                "jobDescription": "Research and data analysis.",
            },
        ]
        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                payload = {
                    "type": "cover",
                    "language": scenario["language"],
                    "fullName": "Ayu Sample",
                    "jobTitle": scenario["jobTitle"],
                    "companyName": scenario["companyName"],
                    "date": "2026-11-09",
                    "coverDetails": scenario["coverDetails"],
                    "jobDescription": scenario["jobDescription"],
                    "resumeText": scenario.get("resumeText", ""),
                }
                content, _, fields = generate_document(payload)
                self.assertIn(scenario["jobTitle"], content)
                self.assertIn(scenario["companyName"], content)
                self.assertIn("Thank you" if scenario["language"] == "en" else "Terima kasih", content)
                self.assertIn(scenario["coverDetails"], content)
                self.assertIn("Sincerely," if scenario["language"] == "en" else "Hormat saya,", content)
                self.assertNotIn("Requirements supported by the experience", content)
                if "not_invented" in scenario:
                    self.assertNotIn(scenario["not_invented"], content.casefold())
                for unsupported_term in scenario.get("not_in_output", ()):
                    self.assertNotIn(unsupported_term.casefold(), content.casefold())
                if scenario["name"] == "incomplete optional information":
                    self.assertIn("Manajer Perekrutan", content)
                    self.assertNotIn("None", content)
                if scenario["name"] == "unrelated skills":
                    self.assertEqual(fields["analysis"]["matchedSkills"], [])
                if scenario["name"] == "long job description":
                    self.assertLessEqual(len(payload["jobDescription"]), 5000)
                    self.assertIn("python", fields["analysis"]["matchedSkills"])

    def test_cover_letter_does_not_duplicate_sentence_punctuation(self) -> None:
        content, _, _ = generate_document(
            {
                "type": "cover",
                "fullName": "Ayu Sample",
                "jobTitle": "Data Analyst",
                "companyName": "Tech Corp Inc.",
                "date": "2026-11-09",
                "coverDetails": "Built a monthly reporting dashboard for a small team.",
            }
        )
        self.assertIn("at Tech Corp Inc.", content)
        self.assertNotIn("Tech Corp Inc..", content)

    def test_cover_letter_limits_profile_to_short_evidence_units(self) -> None:
        profile = (
            "Built a monthly reporting dashboard for a small team. "
            "Reduced manual spreadsheet work by organizing recurring reports. "
            "Also coordinated unrelated office events and meeting schedules."
        )
        content, _, _ = generate_document(
            {
                "type": "cover",
                "fullName": "Ayu Sample",
                "jobTitle": "Reporting Assistant",
                "companyName": "Northstar Analytics",
                "date": "2026-11-09",
                "coverDetails": profile,
            }
        )
        self.assertIn("Built a monthly reporting dashboard", content)
        self.assertIn("Reduced manual spreadsheet work", content)
        self.assertNotIn("Also coordinated unrelated office events", content)

    def test_cover_letter_prioritizes_evidence_relevant_to_job_description(self) -> None:
        content, _, fields = generate_document(
            {
                "type": "cover",
                "fullName": "Ayu Sample",
                "jobTitle": "Junior Data Analyst",
                "companyName": "Northstar Analytics",
                "date": "2026-11-09",
                "coverDetails": (
                    "Organized office events for a student association. "
                    "Helped coordinate weekly meeting schedules."
                ),
                "resumeText": (
                    "Used Python to clean survey data for a university project. "
                    "Created SQL queries to prepare a small reporting dataset."
                ),
                "jobDescription": "Python and SQL skills are useful for this role.",
            }
        )

        self.assertIn("Used Python to clean survey data", content)
        self.assertIn("Created SQL queries", content)
        self.assertNotIn("Organized office events", content)
        self.assertNotIn("weekly meeting schedules", content)
        self.assertEqual(fields["analysis"]["matchedSkills"], ["python", "sql"])

    def test_cover_letter_falls_back_to_profile_when_no_job_skills_match(self) -> None:
        content, _, _ = generate_document(
            {
                "type": "cover",
                "fullName": "Ayu Sample",
                "jobTitle": "Community Coordinator",
                "companyName": "Harbor Group",
                "date": "2026-11-09",
                "coverDetails": (
                    "Volunteered at a community garden. "
                    "Organized weekend activities for local residents."
                ),
                "resumeText": "Maintained a personal collection of travel photographs.",
                "jobDescription": "A positive attitude and curiosity are welcome.",
            }
        )

        self.assertIn("Volunteered at a community garden", content)
        self.assertIn("Organized weekend activities", content)
        self.assertNotIn("travel photographs", content)

    def test_cover_letter_uses_only_user_supplied_claims(self) -> None:
        content, _, _ = generate_document(
            {
                "type": "cover",
                "fullName": "Ayu Sample",
                "jobTitle": "Data Analyst",
                "companyName": "Northstar Analytics",
                "date": "2026-11-09",
                "coverDetails": "Completed a Python data-cleaning project for a university course.",
                "jobDescription": (
                    "The ideal candidate has five years of experience, advanced SQL, "
                    "and a record of increasing revenue by 40 percent."
                ),
            }
        )
        self.assertIn("Python data-cleaning project", content)
        self.assertNotIn("five years", content.casefold())
        self.assertNotIn("advanced SQL", content)
        self.assertNotIn("40 percent", content)

    def test_resignation_quality_scenarios(self) -> None:
        scenarios = [
            ("standard English", "en", "standard", "professional", "", "2026-11-30"),
            ("formal English without last day", "en", "standard", "formal", "", ""),
            ("friendly personal English", "en", "personal", "friendly", "I am taking time to care for family.", ""),
            ("career change English with context", "en", "career_change", "professional", "I plan to move into product design.", ""),
            ("standard Indonesian", "id", "standard", "professional", "", "2026-11-30"),
            ("personal Indonesian without context", "id", "personal", "formal", "", ""),
            ("career change Indonesian with context", "id", "career_change", "friendly", "Saya akan beralih ke bidang riset.", ""),
            ("immediate request Indonesian", "id", "immediate_request", "professional", "This reason must not be added.", "2026-11-10"),
        ]
        for name, language, scenario, tone, reason, last_day in scenarios:
            with self.subTest(scenario=name):
                payload = {
                    "type": "resignation",
                    "language": language,
                    "scenario": scenario,
                    "tone": tone,
                    "fullName": "Sari Putri",
                    "jobTitle": "Operations Analyst",
                    "companyName": "Northstar Group",
                    "date": "2026-11-09",
                    "reason": reason,
                    "lastWorkingDay": last_day,
                }
                content, _, _ = generate_document(payload)
                self.assertIn("Northstar Group", content)
                self.assertIn(
                    "November 9, 2026" if language == "en" else "9 November 2026",
                    content,
                )
                expected_signoff = (
                    "Best regards," if tone == "friendly" and language == "en"
                    else "Salam hangat," if tone == "friendly"
                    else "Sincerely," if language == "en"
                    else "Hormat saya,"
                )
                self.assertIn(expected_signoff, content)
                if last_day:
                    formatted_last_day = (
                        "November 30, 2026" if language == "en" and last_day.endswith("30")
                        else "November 10, 2026" if language == "en"
                        else "30 November 2026" if last_day.endswith("30")
                        else "10 November 2026"
                    )
                    self.assertIn(formatted_last_day, content)
                if reason:
                    if scenario == "immediate_request":
                        self.assertNotIn(reason, content)
                    else:
                        self.assertIn(reason.rstrip("."), content)
                if scenario == "career_change" and reason:
                    self.assertNotIn("pursue a new direction in my career", content)
                    self.assertNotIn("arah karier yang baru", content)
                if scenario == "immediate_request":
                    self.assertIn("Saya memohon", content)
                    self.assertIn("dibicarakan dan disepakati", content)
                    self.assertNotIn("notice period", content.casefold())

    def test_cover_letter_matches_only_skills_present_in_user_provided_evidence(self) -> None:
        content, _, fields = generate_document(
            {
                "type": "cover",
                "language": "id",
                "fullName": "Sari Putri",
                "jobTitle": "Analis Data",
                "companyName": "Nusantara Labs",
                "date": "2026-11-09",
                "coverDetails": "Saya membantu tim membuat dashboard.",
                "resumeText": "Menggunakan Python untuk analisis data dan membuat laporan.",
                "jobDescription": "Dibutuhkan Python, analisis data, kepemimpinan, dan SQL.",
            }
        )

        self.assertEqual(fields["analysis"]["matchedSkills"], ["analitik", "python"])
        self.assertEqual(fields["analysis"]["skillsToAddress"], ["kepemimpinan", "sql"])
        self.assertIn("Menggunakan Python untuk analisis data", content)
        self.assertIn("Saya membantu tim membuat dashboard.", content)
        self.assertNotIn("saya memiliki pengalaman SQL", content.lower())

    def test_immediate_resignation_is_a_request_not_an_assumed_entitlement(self) -> None:
        content, _, _ = generate_document(
            {
                "type": "resignation",
                "scenario": "immediate_request",
                "fullName": "Ada Lovelace",
                "jobTitle": "Engineer",
                "companyName": "Analytical Engines",
                "date": "2026-11-09",
                "lastWorkingDay": "2026-11-10",
            }
        )
        self.assertIn("I respectfully request", content)
        self.assertIn("should be discussed and confirmed", content)

    def test_resignation_scenarios_and_tones_work_in_both_languages(self) -> None:
        scenarios = ("standard", "personal", "career_change", "immediate_request")
        for language in ("en", "id"):
            for tone in ("formal", "professional", "friendly"):
                for scenario in scenarios:
                    payload = {
                        "type": "resignation",
                        "language": language,
                        "tone": tone,
                        "scenario": scenario,
                        "fullName": "Sari Putri",
                        "jobTitle": "Designer",
                        "companyName": "Studio Contoh",
                        "date": "2026-11-09",
                    }
                    if scenario == "immediate_request":
                        payload["lastWorkingDay"] = "2026-11-10"
                    content, _, fields = generate_document(payload)
                    self.assertEqual(fields["scenario"], scenario)
                    self.assertIn("2026", content)
                    if scenario == "immediate_request":
                        request_phrase = "Saya memohon" if language == "id" else "I respectfully request"
                        self.assertIn(request_phrase, content)

    def test_cover_letter_tones_are_valid_in_both_languages(self) -> None:
        for language in ("en", "id"):
            for tone in ("formal", "confident", "warm", "concise"):
                content, _, fields = generate_document(
                    {
                        "type": "cover",
                        "language": language,
                        "tone": tone,
                        "fullName": "Sari Putri",
                        "jobTitle": "Designer",
                        "companyName": "Studio Contoh",
                        "date": "2026-11-09",
                        "coverDetails": "Designed reusable templates for a small team.",
                    }
                )
                self.assertEqual(fields["tone"], tone)
                self.assertIn("Designed reusable templates", content)

    def test_document_generator_rejects_invalid_dates_and_missing_cover_details(self) -> None:
        payload = {
            "type": "resignation",
            "fullName": "Ada",
            "jobTitle": "Engineer",
            "companyName": "Engines",
            "date": "not-a-date",
        }
        with self.assertRaises(APIError):
            generate_document(payload)

        payload.update({"type": "cover", "date": "2026-11-09"})
        with self.assertRaises(APIError):
            generate_document(payload)
        payload.update({"type": "resignation", "language": "xx"})
        with self.assertRaises(APIError):
            generate_document(payload)

    def test_letter_pdf_contains_the_generated_letter_text(self) -> None:
        content, _, fields = generate_document(
            {
                "type": "resignation",
                "fullName": "PDF Content Test",
                "jobTitle": "Engineer",
                "companyName": "Reliable Tools",
                "recipientName": "Hiring Team",
                "email": "pdf@example.com",
                "date": "2026-11-09",
                "reason": "a new opportunity",
            }
        )
        pdf_bytes = _create_document_pdf(content, fields["type"])
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=True)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages).replace("\xa0", " ")

        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Resignation Letter", extracted_text)
        self.assertIn("PDF Content Test", extracted_text)
        self.assertIn("Reliable Tools", extracted_text)
        self.assertIn("The consideration behind my decision is: a new opportunity.", extracted_text)
        self.assertIn("1 / 1", extracted_text)

    def test_letter_pdf_embeds_a_local_font_for_cjk_characters(self) -> None:
        content, _, fields = generate_document(
            {
                "type": "resignation",
                "fullName": "Zoë 李",
                "jobTitle": "Engineer",
                "companyName": "Café & Co",
                "date": "2026-11-09",
            }
        )
        try:
            pdf_bytes = _create_document_pdf(content, fields["type"])
        except APIError as error:
            if error.code == "unsupported_characters":
                self.skipTest("No installed PDF font supports the test's CJK character.")
            raise

        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            extracted_text = "\n".join(page.get_text() for page in document).replace("\xa0", " ")
        self.assertIn("Zoë 李", extracted_text)
        self.assertIn("Café & Co", extracted_text)

    def test_letter_pdf_reports_unsupported_emoji_instead_of_replacing_it(self) -> None:
        content, _, fields = generate_document(
            {
                "type": "resignation",
                "fullName": "Candidate 😊",
                "jobTitle": "Engineer",
                "companyName": "Reliable Tools",
                "date": "2026-11-09",
            }
        )
        with self.assertRaises(APIError) as raised:
            _create_document_pdf(content, fields["type"])
        self.assertEqual(raised.exception.code, "unsupported_characters")

    def test_long_cover_letter_pdf_paginates_without_losing_text(self) -> None:
        # Exercise PDF pagination independently from the cover-letter evidence
        # selector, which intentionally limits profile evidence to two concise units.
        details = "\n".join(
            f"Project {number}: delivered reliable systems and documented measurable results."
            for number in range(55)
        )
        content = "\n".join(
            [
                "Long Letter Candidate",
                "November 9, 2026",
                "Hiring Manager",
                "Reliable Tools",
                "Re: Application for Engineer",
                "Dear Hiring Manager,",
                "I am applying for the Engineer position at Reliable Tools.",
                details,
                "Thank you for your time and consideration.",
                "Sincerely,",
                "Long Letter Candidate",
            ]
        )
        pdf_bytes = _create_document_pdf(content, "cover")
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=True)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages).replace("\xa0", " ")

        self.assertGreater(len(reader.pages), 1)
        self.assertIn("Project 0:", extracted_text)
        self.assertIn("Project 54:", extracted_text)
        self.assertIn(f"{len(reader.pages)} / {len(reader.pages)}", extracted_text)

    def test_pdf_download_api_verifies_content(self) -> None:
        payload = {
            "type": "resignation",
            "fullName": "API Download Test",
            "jobTitle": "Engineer",
            "companyName": "Reliable Tools",
            "date": "2026-11-09",
        }
        response = self.client.post("/api/documents/pdf", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF-"))
        self.assertEqual(response.mimetype, "application/pdf")
        extracted_text = "\n".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(response.data)).pages
        ).replace("\xa0", " ")
        self.assertIn("API Download Test", extracted_text)
        self.assertIn("Reliable Tools", extracted_text)

    def test_document_downloads_export_user_edited_content_as_pdf_and_docx(self) -> None:
        payload = {
            "type": "cover",
            "fullName": "Sari Putri",
            "jobTitle": "Analyst",
            "companyName": "Nusantara Labs",
            "date": "2026-11-09",
            "coverDetails": "Built reporting dashboards for a research team.",
            "content": "Sari Putri\n\nEdited draft: a verified result from my own work.",
        }

        pdf_response = self.client.post("/api/documents/pdf", json=payload)
        self.assertEqual(pdf_response.status_code, 200)
        pdf_text = "\n".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_response.data)).pages
        ).replace("\xa0", " ")
        self.assertIn("Edited draft: a verified result from my own work.", pdf_text)

        docx_response = self.client.post("/api/documents/docx", json=payload)
        self.assertEqual(docx_response.status_code, 200)
        self.assertEqual(
            docx_response.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        paragraphs = Document(io.BytesIO(docx_response.data)).paragraphs
        docx_text = "\n".join(paragraph.text for paragraph in paragraphs)
        self.assertIn("Edited draft: a verified result from my own work.", docx_text)
        self.assertNotIn("X-Remaining-Uses", docx_response.headers)

    def test_docx_export_verifies_nonempty_letter_content(self) -> None:
        with self.assertRaises(APIError):
            _create_document_docx(" \n ", "resignation", "en")

        response = self.client.post(
            "/api/documents/docx",
            json={
                "type": "resignation",
                "fullName": "Ada Lovelace",
                "jobTitle": "Engineer",
                "companyName": "Analytical Engines",
                "date": "2026-11-09",
                "content": " ",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_letter_pdf_download_rejects_empty_render(self) -> None:
        payload = {
            "type": "resignation",
            "fullName": "API Download Test",
            "jobTitle": "Engineer",
            "companyName": "Reliable Tools",
            "date": "2026-11-09",
        }
        with patch("app._create_document_pdf", return_value=b"%PDF-empty-render"):
            response = self.client.post("/api/documents/pdf", json=payload)

        self.assertEqual(response.status_code, 500)

    def test_invalid_letter_pdf_request_is_rejected(self) -> None:
        response = self.client.post("/api/documents/pdf", json={"type": "resignation"})

        self.assertEqual(response.status_code, 400)

    def test_caption_respects_x_character_limit_and_platform_hashtag_limit(self) -> None:
        content, settings = generate_caption(
            {
                "category": "food",
                "platform": "x",
                "tone": "friendly",
                "topic": "A" * 1000,
                "audience": "new customers",
                "callToAction": "",
                "hashtagCount": "10",
            }
        )
        self.assertLessEqual(len(content), 280)
        self.assertEqual(settings["platform"], "x")
        hashtags = [word for word in content.split() if word.startswith("#")]
        self.assertLessEqual(len(hashtags), 3)

    def test_caption_adds_indonesian_value_and_repeatable_relevant_hashtags(self) -> None:
        payload = {
            "category": "food",
            "platform": "instagram",
            "language": "id",
            "tone": "friendly",
            "topic": "Kopi susu gula aren",
            "audience": "pecinta kopi",
            "keyBenefit": "dibuat segar setiap pagi",
            "hashtagCount": "3",
        }
        content, settings = generate_caption(payload)
        repeated_content, _ = generate_caption(payload)

        self.assertEqual(content, repeated_content)
        self.assertIn("dibuat segar setiap pagi", content)
        self.assertIn("Lihat detailnya.", content)
        self.assertTrue(any(tag in content for tag in ("#MakanEnak", "#RasaNusantara", "#TempatMakan")))
        self.assertEqual(settings["language"], "id")
        self.assertEqual(settings["keyBenefit"], "dibuat segar setiap pagi")

    def test_caption_normalizes_pasted_line_breaks_in_user_fields(self) -> None:
        content, settings = generate_caption(
            {
                "category": "services",
                "platform": "instagram",
                "language": "en",
                "tone": "professional",
                "objective": "promotion",
                "topic": "Bookkeeping\nservices\tfor small shops",
                "audience": "independent\nshop owners",
                "keyBenefit": "clear monthly\nreports",
                "callToAction": "Get in touch\nthis week",
                "hashtagCount": "0",
            }
        )

        self.assertIn("Bookkeeping services for small shops", content)
        self.assertIn("Created for independent shop owners.", content)
        self.assertIn("clear monthly reports", content)
        self.assertIn("Get in touch this week", content)
        self.assertNotIn("Bookkeeping\nservices", content)
        self.assertEqual(settings["topic"], "Bookkeeping services for small shops")
        self.assertEqual(settings["audience"], "independent shop owners")
        self.assertEqual(settings["keyBenefit"], "clear monthly reports")
        self.assertEqual(settings["callToAction"], "Get in touch this week")

    def test_caption_rejects_unsupported_settings(self) -> None:
        with self.assertRaises(APIError):
            generate_caption({"category": "unknown"})
        with self.assertRaises(APIError):
            generate_caption(
                {
                    "category": "food",
                    "platform": "x",
                    "tone": "friendly",
                    "topic": "Test",
                    "hashtagCount": 3.5,
                }
            )
        with self.assertRaises(APIError):
            generate_caption(
                {
                    "category": "food",
                    "platform": "instagram",
                    "tone": "friendly",
                    "language": "xx",
                    "topic": "Test",
                }
            )

    def test_caption_x_length_matches_browser_utf16_counter(self) -> None:
        content, _ = generate_caption(
            {
                "category": "food",
                "platform": "x",
                "tone": "friendly",
                "topic": "🍜" * 250,
                "hashtagCount": "3",
            }
        )
        browser_character_count = len(content.encode("utf-16-le")) // 2
        self.assertLessEqual(browser_character_count, 280)

    def test_indonesian_x_caption_with_benefit_stays_within_utf16_limit(self) -> None:
        content, _ = generate_caption(
            {
                "category": "services",
                "platform": "x",
                "language": "id",
                "tone": "persuasive",
                "topic": "Layanan konsultasi bisnis untuk usaha kecil " * 8,
                "keyBenefit": "Membantu merapikan alur kerja dan menghemat waktu",
                "hashtagCount": "10",
            }
        )
        self.assertLessEqual(len(content.encode("utf-16-le")) // 2, 280)
        self.assertLessEqual(sum(word.startswith("#") for word in content.split()), 3)

    def test_caption_supports_all_platforms_objectives_tones_and_optional_hashtags(self) -> None:
        platforms = ("instagram", "tiktok", "facebook", "linkedin", "x", "youtube")
        tones = ("professional", "casual", "friendly", "persuasive", "educational", "humorous", "minimal")
        objectives = (
            "promotion", "engagement", "education", "brand_awareness",
            "storytelling", "sales_conversion", "personal_branding",
        )
        for platform in platforms:
            for tone in tones:
                for objective in objectives:
                    content, settings = generate_caption(
                        {
                            "category": "services",
                            "platform": platform,
                            "tone": tone,
                            "objective": objective,
                            "topic": "A practical planning service",
                            "hashtagCount": "0",
                        }
                    )
                    self.assertEqual(settings["platform"], platform)
                    self.assertEqual(settings["tone"], tone)
                    self.assertEqual(settings["objective"], objective)
                    self.assertEqual(len(settings["variants"]), 3)
                    self.assertEqual(len(set(settings["variants"])), 3)
                    self.assertEqual(len(settings["ctaSuggestions"]), 3)
                    self.assertNotIn("#", content)
                    if platform == "x":
                        self.assertLessEqual(len(content.encode("utf-16-le")) // 2, 280)

    def test_indonesian_youtube_caption_returns_platform_specific_cta_suggestions(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key-not-real"
        with patch("app._gemini_json", return_value={"variants": ["Caption satu", "Caption dua", "Caption tiga"], "ctaSuggestions": ["Subscribe sekarang", "Bagikan", "Komentar"]}):
            response = self.client.post(
                "/api/captions/generate",
                json={
                    "category": "tech",
                    "platform": "youtube",
                    "language": "id",
                    "tone": "educational",
                    "objective": "education",
                    "topic": "Keamanan akun digital",
                    "hashtagCount": 3,
                },
            )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(len(result["variants"]), 3)
        self.assertEqual(len(result["ctaSuggestions"]), 3)
        self.assertTrue(any("Subscribe" in suggestion for suggestion in result["ctaSuggestions"]))
        self.assertIn("objective", result["settings"])
        self.assertIn("#KeamananAkunDigital", result["content"])

    def test_caption_quality_scenarios(self) -> None:
        scenarios = [
            ("restaurant promotion", "food", "instagram", "id", "promotion", "friendly", "Menu makan siang dengan bahan lokal", "pekerja kantor", "disiapkan segar setiap pagi"),
            ("education video", "tech", "youtube", "en", "education", "educational", "How to recognize phishing links", "new internet users", "three simple warning signs"),
            ("personal branding", "services", "linkedin", "en", "personal_branding", "professional", "Lessons from my first year as a product designer", "early-career designers", "weekly research notes"),
            ("small business fashion", "fashion", "facebook", "id", "sales_conversion", "persuasive", "Koleksi kain lokal dari perajin keluarga", "pencinta produk lokal", "dibuat dalam jumlah terbatas"),
            ("technology TikTok", "tech", "tiktok", "en", "promotion", "casual", "Pocket-sized rechargeable reading lamp", "frequent travelers", "USB-C charging"),
            ("restaurant story", "food", "instagram", "en", "storytelling", "friendly", "A family bakery recipe passed down for generations", "neighborhood families", "baked in small batches"),
            ("professional LinkedIn", "services", "linkedin", "id", "engagement", "professional", "Cara tim kecil menyusun proses onboarding", "pemimpin tim baru", "langkah kerja yang terdokumentasi"),
            ("fashion X", "fashion", "x", "en", "brand_awareness", "minimal", "Everyday linen shirt in four neutral colors", "minimalist wardrobes", "natural linen fabric"),
            ("technology product", "tech", "facebook", "en", "promotion", "persuasive", "Noise-cancelling headphones with replaceable ear pads", "daily commuters", "replaceable ear pads"),
            ("service conversion", "services", "youtube", "id", "sales_conversion", "friendly", "Konsultasi pembukuan untuk usaha kecil", "pemilik usaha kecil", "sesi awal selama 30 menit"),
            ("playful coffee post", "food", "tiktok", "id", "engagement", "humorous", "Es kopi susu tanpa tambahan sirup", "penggemar kopi", "rasa kopi yang tetap terasa"),
            ("security education", "tech", "instagram", "id", "education", "educational", "Cara mengaktifkan autentikasi dua faktor", "pengguna akun digital", "satu lapis perlindungan tambahan"),
            ("sustainable fashion story", "fashion", "instagram", "id", "storytelling", "friendly", "Cerita jaket dari kain daur ulang", "pembeli yang peduli lingkungan", "memanfaatkan bahan sisa"),
            ("service brand awareness", "services", "linkedin", "en", "brand_awareness", "casual", "Independent bookkeeping for neighborhood shops", "local shop owners", "clear monthly reports"),
            ("food engagement on X", "food", "x", "id", "engagement", "casual", "Sarapan cepat untuk pekerja yang berangkat pagi", "pekerja dengan jadwal padat", "siap dalam beberapa menit"),
        ]
        for name, category, platform, language, objective, tone, topic, audience, benefit in scenarios:
            with self.subTest(scenario=name):
                content, settings = generate_caption(
                    {
                        "category": category,
                        "platform": platform,
                        "language": language,
                        "objective": objective,
                        "tone": tone,
                        "topic": topic,
                        "audience": audience,
                        "keyBenefit": benefit,
                        "hashtagCount": "5",
                    }
                )
                variants = settings["variants"]
                self.assertEqual(len(variants), 3)
                self.assertEqual(len(set(variants)), 3)
                self.assertTrue(all(topic in variant for variant in variants))
                self.assertTrue(all(audience in variant for variant in variants))
                self.assertTrue(all(benefit in variant for variant in variants))
                self.assertIn(settings["ctaSuggestions"][0], content)
                tags = [word for word in content.split() if word.startswith("#")]
                self.assertLessEqual(len(tags), 5 if platform not in {"linkedin", "x"} else 3)
                self.assertNotIn("#How", tags)
                self.assertNotIn("#With", tags)
                self.assertNotIn("#What", tags)
                self.assertNotIn("#Cara", tags)
                if name == "security education":
                    self.assertIn("#AutentikasiDuaFaktor", tags)
                if platform == "x":
                    self.assertLessEqual(len(content.encode("utf-16-le")) // 2, 280)

    def test_usage_is_unlimited_and_quota_endpoints_are_removed(self) -> None:
        self.assertNotIn("quota", self.client.get("/api/session").get_json())
        self.assertEqual(self.client.get("/api/quota").status_code, 404)
        self.assertEqual(
            self.client.post("/api/quota/consume", json={"action": "copy"}).status_code,
            404,
        )

        payload = {
            "type": "resignation",
            "fullName": "Unlimited User",
            "jobTitle": "Engineer",
            "companyName": "Reliable Tools",
            "date": "2026-11-09",
        }
        for _ in range(5):
            with self.subTest(export_number=_):
                response = self.client.post("/api/documents/pdf", json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data.startswith(b"%PDF-"))

    def test_library_persists_per_browser_session(self) -> None:
        response = self.client.post(
            "/api/library",
            json={
                "kind": "caption",
                "title": "Post",
                "content": "Hello #World",
                "data": {"platform": "instagram"},
            },
        )
        self.assertEqual(response.status_code, 201)
        item = response.get_json()
        self.assertEqual(self.client.get("/api/library").get_json()["items"][0]["id"], item["id"])

        another_browser = self.app.test_client()
        self.assertEqual(another_browser.get("/api/library").get_json()["items"], [])
        self.assertEqual(
            self.client.delete(f"/api/library/{item['id']}").get_json(),
            {"deleted": True},
        )
        self.assertEqual(self.client.get("/api/library").get_json()["items"], [])

    def test_library_survives_app_restart_with_same_database_and_browser_cookie(self) -> None:
        saved = self.client.post(
            "/api/library",
            json={
                "kind": "caption",
                "title": "Persistent draft",
                "content": "This entry should survive an application restart.",
                "data": {"platform": "linkedin"},
            },
        )
        self.assertEqual(saved.status_code, 201)
        saved_item_id = saved.get_json()["id"]

        session_cookie = self.client.get_cookie("session")
        self.assertIsNotNone(session_cookie, "Saving an item should establish a browser session cookie")

        # Recreate the Flask application against the same SQLite file, as if the
        # local server had stopped and started again. Reuse the browser cookie
        # to represent the same browser returning after the restart.
        restarted_app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": self.app.config["DATABASE"],
            }
        )
        restarted_client = restarted_app.test_client()
        restarted_client.set_cookie("session", session_cookie.value)

        restored_items = restarted_client.get("/api/library").get_json()["items"]
        self.assertEqual(len(restored_items), 1)
        self.assertEqual(restored_items[0]["id"], saved_item_id)
        self.assertEqual(restored_items[0]["title"], "Persistent draft")
        self.assertEqual(
            restored_items[0]["content"],
            "This entry should survive an application restart.",
        )

    def test_security_headers_are_present_on_html_and_api_responses(self) -> None:
        for response in (self.client.get("/"), self.client.get("/api/session")):
            with self.subTest(path=response.request.path):
                self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
                self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
                self.assertEqual(
                    response.headers.get("Referrer-Policy"),
                    "strict-origin-when-cross-origin",
                )
                self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_production_mode_requires_an_explicit_secret_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"BORINGSTUFF_ENV": "production"}, clear=False):
                with patch.dict("os.environ", {"BORINGSTUFF_SECRET_KEY": ""}):
                    with self.assertRaisesRegex(RuntimeError, "BORINGSTUFF_SECRET_KEY"):
                        create_app({"INSTANCE_PATH": directory, "DATABASE": str(Path(directory) / "db.sqlite3")})

    def test_production_mode_rejects_short_secret_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                "BORINGSTUFF_ENV": "production",
                "BORINGSTUFF_SECRET_KEY": "too-short",
                "BORINGSTUFF_ALLOWED_HOSTS": "example.com",
            }
            with patch.dict("os.environ", environment, clear=False):
                with self.assertRaisesRegex(RuntimeError, "at least 32 characters"):
                    create_app({"INSTANCE_PATH": directory, "DATABASE": str(Path(directory) / "db.sqlite3")})

    def test_production_mode_requires_explicit_allowed_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                "BORINGSTUFF_ENV": "production",
                "BORINGSTUFF_SECRET_KEY": "production-test-secret-0123456789-strong",
                "BORINGSTUFF_ALLOWED_HOSTS": "",
            }
            with patch.dict("os.environ", environment, clear=False):
                with self.assertRaisesRegex(RuntimeError, "BORINGSTUFF_ALLOWED_HOSTS"):
                    create_app({"INSTANCE_PATH": directory, "DATABASE": str(Path(directory) / "db.sqlite3")})

    def test_production_mode_rejects_url_or_wildcard_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                "BORINGSTUFF_ENV": "production",
                "BORINGSTUFF_SECRET_KEY": "production-test-secret-0123456789-strong",
                "BORINGSTUFF_ALLOWED_HOSTS": "https://example.com,*",
            }
            with patch.dict("os.environ", environment, clear=False):
                with self.assertRaisesRegex(RuntimeError, "hostnames only"):
                    create_app({"INSTANCE_PATH": directory, "DATABASE": str(Path(directory) / "db.sqlite3")})

    def test_production_mode_uses_secure_cookies_and_trusted_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {
                "BORINGSTUFF_ENV": "production",
                "BORINGSTUFF_SECRET_KEY": "production-test-secret-0123456789-strong",
                "BORINGSTUFF_ALLOWED_HOSTS": "example.com,www.example.com",
            }
            with patch.dict("os.environ", environment, clear=False):
                app = create_app({
                    "TESTING": True,
                    "INSTANCE_PATH": directory,
                    "DATABASE": str(Path(directory) / "production.sqlite3"),
                })
            self.assertTrue(app.config["SESSION_COOKIE_SECURE"])
            self.assertEqual(app.config["TRUSTED_HOSTS"], ["example.com", "www.example.com"])
            self.assertEqual(app.config["PREFERRED_URL_SCHEME"], "https")
            response = app.test_client().get("/", headers={"Host": "example.com"})
            self.assertEqual(response.status_code, 200)

    def test_robots_txt_blocks_api_from_crawling(self) -> None:
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User-agent: *", response.data)
        self.assertIn(b"Allow: /", response.data)
        self.assertIn(b"Disallow: /api/", response.data)
        self.assertNotIn(b"Sitemap:", response.data)
        self.assertIn("public", response.headers.get("Cache-Control", ""))

    def test_sitemap_uses_only_configured_public_base_url(self) -> None:
        missing_url = self.client.get("/sitemap.xml")
        self.assertEqual(missing_url.status_code, 404)

        self.app.config["PUBLIC_BASE_URL"] = "https://www.boringstuff.com"
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/xml")
        self.assertIn(b"https://www.boringstuff.com/", response.data)
        self.assertNotIn(b"127.0.0.1", response.data)

    def test_library_item_cannot_be_read_or_deleted_from_another_session(self) -> None:
        response = self.client.post(
            "/api/library",
            json={
                "kind": "document",
                "title": "Private draft",
                "content": "Private content",
                "data": {},
            },
        )
        self.assertEqual(response.status_code, 201)
        item_id = response.get_json()["id"]

        another_browser = self.app.test_client()
        self.assertEqual(another_browser.get("/api/library").get_json()["items"], [])
        delete_response = another_browser.delete(f"/api/library/{item_id}")
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(self.client.get("/api/library").get_json()["items"][0]["id"], item_id)

    def test_library_rejects_non_json_data_and_oversized_metadata(self) -> None:
        invalid_data = self.client.post(
            "/api/library",
            json={"kind": "caption", "content": "Draft", "data": ["not", "an object"]},
        )
        self.assertEqual(invalid_data.status_code, 400)
        self.assertIn("data must be a JSON object", invalid_data.get_json()["error"])

        oversized_data = self.client.post(
            "/api/library",
            json={"kind": "caption", "content": "Draft", "data": {"notes": "x" * 21000}},
        )
        self.assertEqual(oversized_data.status_code, 400)
        self.assertIn("data is too large", oversized_data.get_json()["error"])

    def test_library_has_no_item_count_limit(self) -> None:
        for index in range(55):
            response = self.client.post(
                "/api/library",
                json={
                    "kind": "caption",
                    "title": f"Post {index}",
                    "content": "Saved test content",
                    "data": {},
                },
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.client.get("/api/library").get_json()["items"]), 55)

    def test_pdf_endpoint_returns_optimized_file_without_quota_headers(self) -> None:
        source_document = pymupdf.open()
        source_document.new_page().insert_text((72, 72), "Verified compression output")
        optimized_pdf = source_document.tobytes()
        source_document.close()
        original_pdf = optimized_pdf + b"\n%" + (b"padding " * 300)
        with patch("app._compress_text_safe", return_value=optimized_pdf):
            response = self.client.post(
                "/api/pdf/compress",
                data={
                    "mode": "lossless",
                    "file": (io.BytesIO(original_pdf), "original.pdf"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, optimized_pdf)
        self.assertEqual(response.headers["X-Page-Count"], "1")
        self.assertEqual(response.headers["X-Text-Status"], "preserved")
        self.assertNotIn("X-Quota-Date", response.headers)
        self.assertNotIn("X-Remaining-Uses", response.headers)

    def test_pdf_compression_rejects_page_count_change(self) -> None:
        source_document = pymupdf.open()
        source_document.new_page().insert_text((72, 72), "Original")
        original_pdf = source_document.tobytes()
        source_document.close()
        output_document = pymupdf.open()
        output_document.new_page().insert_text((72, 72), "Changed page one")
        output_document.new_page().insert_text((72, 72), "Unexpected page two")
        invalid_output = output_document.tobytes()
        output_document.close()
        padded_original = original_pdf + b"\n%" + (b"padding " * 300)

        with patch("app._compress_text_safe", return_value=invalid_output):
            response = self.client.post(
                "/api/pdf/compress",
                data={
                    "mode": "lossless",
                    "file": (io.BytesIO(padded_original), "original.pdf"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["code"], "verification_failed")

    def test_lossless_pdf_compression_rejects_changed_text(self) -> None:
        source_document = pymupdf.open()
        source_document.new_page().insert_text((72, 72), "Source text")
        original_pdf = source_document.tobytes()
        source_document.close()
        output_document = pymupdf.open()
        output_document.new_page().insert_text((72, 72), "Different text")
        invalid_output = output_document.tobytes()
        output_document.close()

        with patch("app._compress_text_safe", return_value=invalid_output):
            response = self.client.post(
                "/api/pdf/compress",
                data={
                    "mode": "lossless",
                    "file": (io.BytesIO(original_pdf + b"\n%" + b"x" * 2048), "original.pdf"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["code"], "verification_failed")

    def test_lossless_pdf_reports_when_source_has_no_extractable_text(self) -> None:
        source_document = pymupdf.open()
        source_document.new_page()
        original_pdf = source_document.tobytes()
        source_document.close()

        with patch("app._compress_text_safe", return_value=original_pdf):
            response = self.client.post(
                "/api/pdf/compress",
                data={
                    "mode": "lossless",
                    "file": (io.BytesIO(original_pdf + b"\n%" + b"x" * 2048), "scan.pdf"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Text-Status"], "none")

    def test_invalid_pdf_is_rejected(self) -> None:
        response = self.client.post(
            "/api/pdf/compress",
            data={
                "mode": "lossless",
                "file": (io.BytesIO(b"not a PDF"), "bad.pdf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    def test_real_image_compression_keeps_page_count_and_dimensions(self) -> None:
        source_document = pymupdf.open()
        page = source_document.new_page(width=400, height=600)
        page.insert_text((40, 60), "Readable source text")
        source = source_document.tobytes()
        source_document.close()

        optimized = _compress_image_pdf(source, "balanced")
        with pymupdf.open(stream=optimized, filetype="pdf") as output_document:
            self.assertEqual(output_document.page_count, 1)
            self.assertEqual(output_document[0].rect.width, 400)
            self.assertEqual(output_document[0].rect.height, 600)
            self.assertEqual(output_document[0].get_text().strip(), "")
        self.assertEqual(len(PdfReader(io.BytesIO(optimized)).pages), 1)

    def test_real_text_safe_compression_preserves_selectable_text(self) -> None:
        source_document = pymupdf.open()
        source_document.new_page().insert_text((72, 72), "Selectable test text")
        source = source_document.tobytes()
        source_document.close()

        optimized = _compress_text_safe(source)
        reader = PdfReader(io.BytesIO(optimized))
        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Selectable test text", reader.pages[0].extract_text())

    def test_pdf_compression_modes_audit_structure_and_rendered_quality(self) -> None:
        source_document = pymupdf.open()

        text_page = source_document.new_page(width=612, height=792)
        text_page.insert_text((55, 55), "Text-heavy report")
        for index in range(50):
            text_page.insert_text(
                (55, 85 + index * 13),
                f"Selectable paragraph {index}: review the figures and supporting notes.",
                fontsize=9,
            )

        def add_raster_page(title: str) -> None:
            template = pymupdf.open()
            page = template.new_page(width=612, height=792)
            page.draw_rect(
                pymupdf.Rect(45, 50, 565, 740),
                color=(0, 0, 0),
                fill=(0.95, 0.95, 0.95),
                width=1,
            )
            page.insert_text((75, 120), title, fontsize=18)
            for index in range(25):
                page.draw_line(
                    (75, 160 + index * 18),
                    (500, 160 + index * 18),
                    color=(0.2, 0.3, 0.5),
                    width=1,
                )
                page.insert_text(
                    (80, 175 + index * 18),
                    f"Printed line {index} with image details",
                    fontsize=8,
                )
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            raster_page = source_document.new_page(width=612, height=792)
            raster_page.insert_image(raster_page.rect, pixmap=pixmap)
            template.close()

        add_raster_page("Image-heavy brochure")
        add_raster_page("Scanned document")

        for index in range(3):
            page = source_document.new_page(width=612, height=792)
            page.insert_text((55, 65), f"Multi-page report — page {index + 1}")
            page.insert_text((55, 95), "The page count must remain unchanged.")

        table_page = source_document.new_page(width=612, height=792)
        table_page.insert_text((55, 65), "Quarterly table")
        for x in range(60, 501, 110):
            table_page.draw_line((x, 110), (x, 300), width=0.5)
        for y in range(110, 301, 30):
            table_page.draw_line((60, y), (500, y), width=0.5)
        for row in range(5):
            table_page.insert_text((65, 130 + row * 30), f"row {row}: item value", fontsize=9)

        special_page = source_document.new_page(width=612, height=792)
        special_page.insert_text((55, 65), "Special characters: café, naïve, résumé — €")

        link_page = source_document.new_page(width=612, height=792)
        link_page.insert_text((55, 65), "Document containing a retained web link")
        link_page.insert_link(
            {
                "kind": pymupdf.LINK_URI,
                "from": pymupdf.Rect(55, 100, 260, 135),
                "uri": "https://example.com/report",
            }
        )

        form_page = source_document.new_page(width=612, height=792)
        form_page.insert_text((55, 65), "Document containing an editable text field")
        widget = pymupdf.Widget()
        widget.field_name = "contact_name"
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.rect = pymupdf.Rect(55, 100, 260, 130)
        widget.field_value = "Ayu"
        form_page.add_widget(widget)

        source = source_document.tobytes()
        source_document.close()
        with pymupdf.open(stream=source, filetype="pdf") as source_pdf:
            source_page_count = source_pdf.page_count
            source_text = [" ".join(page.get_text().split()) for page in source_pdf]
            self.assertEqual(source_page_count, 10)
            self.assertEqual(len(source_text[1]), 0)
            self.assertEqual(len(source_text[2]), 0)
            self.assertIn("café", source_text[7])
        source_interactive = _pdf_interactive_content(source)
        self.assertEqual(len(source_interactive[0]), 1)
        self.assertEqual(len(source_interactive[1]), 1)

        for mode in ("lossless", "balanced", "strong"):
            with self.subTest(mode=mode):
                optimized = (
                    _compress_text_safe(source)
                    if mode == "lossless"
                    else _compress_image_pdf(source, mode)
                )
                with (
                    pymupdf.open(stream=source, filetype="pdf") as source_pdf,
                    pymupdf.open(stream=optimized, filetype="pdf") as output_pdf,
                ):
                    self.assertEqual(output_pdf.page_count, source_page_count)
                    output_text = [" ".join(page.get_text().split()) for page in output_pdf]
                    for index, (source_page, output_page) in enumerate(
                        zip(source_pdf, output_pdf)
                    ):
                        self.assertEqual(source_page.rect, output_page.rect)
                        original_pixmap = source_page.get_pixmap(
                            matrix=pymupdf.Matrix(0.75, 0.75),
                            alpha=False,
                        )
                        output_pixmap = output_page.get_pixmap(
                            matrix=pymupdf.Matrix(0.75, 0.75),
                            alpha=False,
                        )
                        differences = [
                            abs(left - right)
                            for left, right in zip(original_pixmap.samples, output_pixmap.samples)
                        ]
                        self.assertEqual(len(differences), len(original_pixmap.samples))
                        mean_pixel_difference = sum(differences) / len(differences)
                        if mode == "lossless":
                            self.assertEqual(output_text, source_text)
                            self.assertEqual(mean_pixel_difference, 0)
                        else:
                            self.assertEqual(output_text[index], "")
                            self.assertGreater(len(output_page.get_images()), 0)
                            self.assertLess(mean_pixel_difference, 15)
                if mode == "lossless":
                    self.assertEqual(_pdf_interactive_content(optimized), source_interactive)
                else:
                    self.assertEqual(_pdf_interactive_content(optimized), ([], []))

    def test_lossless_endpoint_rejects_lost_links_before_download(self) -> None:
        source_document = pymupdf.open()
        page = source_document.new_page()
        page.insert_text((72, 72), "Retain this linked text")
        page.insert_link(
            {
                "kind": pymupdf.LINK_URI,
                "from": pymupdf.Rect(72, 90, 250, 120),
                "uri": "https://example.com/source",
            }
        )
        original_pdf = source_document.tobytes()
        source_document.close()

        plain_document = pymupdf.open()
        plain_document.new_page().insert_text((72, 72), "Retain this linked text")
        output_without_link = plain_document.tobytes()
        plain_document.close()

        with patch("app._compress_text_safe", return_value=output_without_link):
            response = self.client.post(
                "/api/pdf/compress",
                data={
                    "mode": "lossless",
                    "file": (
                        io.BytesIO(original_pdf + b"\n%" + b"padding " * 300),
                        "linked.pdf",
                    ),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["code"], "verification_failed")
        self.assertIn("link or form", response.get_json()["error"])

    def test_image_modes_explain_when_no_smaller_pdf_is_produced(self) -> None:
        document = pymupdf.open()
        document.new_page().insert_text((72, 72), "A short vector-only page")
        source = document.tobytes()
        document.close()

        for mode in ("balanced", "strong"):
            with self.subTest(mode=mode):
                response = self.client.post(
                    "/api/pdf/compress",
                    data={
                        "mode": mode,
                        "file": (io.BytesIO(source), f"{mode}.pdf"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.get_json()["code"], "no_reduction")
                self.assertIn("No smaller version was produced", response.get_json()["error"])
                self.assertIn("original PDF was left unchanged", response.get_json()["error"])

    def test_no_reduction_is_reported_without_consuming_any_usage_limit(self) -> None:
        source_document = pymupdf.open()
        source_document.new_page().insert_text((72, 72), "Small PDF")
        source = source_document.tobytes()
        source_document.close()

        response = self.client.post(
            "/api/pdf/compress",
            data={
                "mode": "lossless",
                "file": (io.BytesIO(source), "small.pdf"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["code"], "no_reduction")

    def test_ai_status_does_not_expose_api_key(self) -> None:
        response = self.client.get("/api/ai/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["enabled"])
        self.assertNotIn("key", response.get_json())

    def test_document_route_requires_gemini_without_fallback(self) -> None:
        response = self.client.post("/api/documents/generate", json={
            "type": "resignation", "fullName": "Ada Lovelace", "jobTitle": "Engineer",
            "companyName": "Analytical Engines", "date": "2026-11-11"
        })
        self.assertEqual(response.status_code, 503)
        self.assertEqual("ai_not_configured", response.get_json()["code"])

    def test_document_route_uses_gemini_when_configured(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key-not-real"
        with patch("app._gemini_text", return_value="Ada Lovelace\nNovember 11, 2026\n\nDear Team,\n\nI am writing to resign from my Engineer role at Analytical Engines.\n\nSincerely,\nAda Lovelace"):
            response = self.client.post("/api/documents/generate", json={
                "type": "resignation", "fullName": "Ada Lovelace", "jobTitle": "Engineer",
                "companyName": "Analytical Engines", "date": "2026-11-11"
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["aiGenerated"])

    def test_short_ai_cover_letter_is_revised_before_success(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key-not-real"
        short = "Alex Morgan\nDear Hiring Manager,\n\nI am applying for this role.\n\nSincerely,\nAlex Morgan"
        long = "\n\n".join([
            "Alex Morgan\nNovember 11, 2026\n\nHiring Manager\nExample Company\n\nRe: Application for Administrative Assistant\n\nDear Hiring Manager,",
            "I am applying for the Administrative Assistant position. My Bachelor's Degree in Business Administration and one year of administrative assistant experience provide a relevant foundation for this role. I have used data entry, Microsoft Word, communication, and document management skills in administrative contexts.",
            "The position's focus on organizing information, maintaining records, and supporting daily operations aligns with the experience and skills I have provided. I understand that accurate records and clear communication help teams coordinate their work. I would bring an organized approach, attention to detail, and a willingness to learn the team's established processes. My academic background in business administration also gives me context for routine office procedures and the importance of consistent documentation.",
            "I would welcome the opportunity to discuss how my background could support your team. Thank you for your time and consideration. I look forward to learning more about your administrative workflow and the priorities of the international team.\n\nSincerely,\nAlex Morgan"
        ])
        with patch("app._gemini_text", side_effect=[short, long]) as mocked:
            response = self.client.post("/api/documents/generate", json={
                "type": "cover", "fullName": "Alex Morgan", "jobTitle": "Administrative Assistant",
                "companyName": "Example Company", "date": "2026-11-11",
                "resumeText": "Bachelor's Degree in Business Administration. 1 year as Administrative Assistant. Skills: Data Entry, Microsoft Word, Communication, Document Management.",
                "jobDescription": "Manage documents, organize data, maintain records, and support daily administrative operations."
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["aiGenerated"])
        self.assertEqual(2, mocked.call_count)
        self.assertGreaterEqual(len(response.get_json()["content"].split()), 160)

    def test_caption_route_uses_three_ai_variants_when_configured(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key-not-real"
        data = {"variants": ["First distinct caption", "A story-led second caption", "A concise third caption"], "ctaSuggestions": ["Save this", "Share this", "Comment below"]}
        with patch("app._gemini_json", return_value=data):
            response = self.client.post("/api/captions/generate", json={
                "category": "tech", "platform": "instagram", "topic": "A new productivity app",
                "tone": "professional", "language": "en", "objective": "education", "hashtagCount": "3"
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["settings"]["aiGenerated"])
        self.assertEqual(3, len(response.get_json()["variants"]))

    def test_resume_analyzer_requires_gemini_and_validates_input(self) -> None:
        missing_key = self.client.post("/api/resume/analyze", json={"resumeText": "Resume", "jobDescription": "Role"})
        self.assertEqual(missing_key.status_code, 503)
        self.app.config["GEMINI_API_KEY"] = "test-key-not-real"
        result = {"score": 82, "summary": "Good alignment", "strengths": ["Python"], "gaps": [], "keywordsToConsider": [], "bulletRewrites": [], "nextSteps": ["Tailor summary"]}
        with patch("app._gemini_json", return_value=result):
            response = self.client.post("/api/resume/analyze", json={"resumeText": "Python developer", "jobDescription": "Python role"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(82, response.get_json()["score"])
        self.assertIn("not an ATS guarantee", response.get_json()["disclaimer"])

    def test_interview_prep_returns_structured_questions(self) -> None:
        self.app.config["GEMINI_API_KEY"] = "test-key-not-real"
        result = {"roleOverview": "Role summary", "questions": [{"type": "Behavioral", "question": f"Question {i}", "whatInterviewerAssesses": "Communication", "answerFramework": "Use STAR"} for i in range(8)], "questionsToAskEmployer": ["What does success look like?"], "preparationChecklist": ["Review examples"]}
        with patch("app._gemini_json", return_value=result):
            response = self.client.post("/api/interview/prepare", json={"jobTitle": "Analyst"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(8, len(response.get_json()["questions"]))


if __name__ == "__main__":
    unittest.main()
