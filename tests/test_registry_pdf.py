import unittest

from app.ocr.registry_pdf import RegistryPdfError, load_registry_pdf


class RegistryPdfTest(unittest.TestCase):
    def test_rejects_non_pdf_bytes_even_when_filename_could_be_pdf(self):
        with self.assertRaises(RegistryPdfError) as raised:
            load_registry_pdf(b"not-a-real-pdf")

        self.assertEqual("NOT_PDF", raised.exception.code)

    def test_rejects_empty_file(self):
        with self.assertRaises(RegistryPdfError) as raised:
            load_registry_pdf(b"")

        self.assertEqual("EMPTY_FILE", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
