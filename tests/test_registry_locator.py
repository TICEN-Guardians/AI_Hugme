import unittest

from app.ocr.registry_locator import (
    RegistryTextLocator,
    rank_is_supported,
    value_is_supported,
)


class RegistryTextLocatorTest(unittest.TestCase):
    def test_receipt_number_requires_its_label_not_unrelated_digits(self):
        self.assertFalse(value_is_supported("제101호", "제1301호"))
        self.assertTrue(value_is_supported("제101호", "접수 제101호"))

    def test_locates_a_right_split_across_adjacent_pages(self):
        pages = (
            "【을구】\n5\n3번근저당권설정등\n2020년 1월 1일",
            "기말소\n제192142호\n해지",
        )
        located = RegistryTextLocator(pages).locate_right(
            section_text="\n".join(pages),
            rank_no="5",
            purpose="3번근저당권설정등기말소",
            receipt_no="제192142호",
            registered_at=None,
            holder=None,
            debtor=None,
            amount=None,
            target_rank_nos=["3"],
            joint_collateral_id=None,
        )

        self.assertIsNotNone(located)
        self.assertEqual((1, 2), located.pages)

    def test_locates_an_owner_whose_address_continues_on_the_next_page(self):
        pages = (
            "소유자 이은원 681130-*******",
            "이은원의 주소 수원시 팔달구 인계동 384 주공아파트 113-105",
        )
        located = RegistryTextLocator(pages).locate_owner(
            name="이은원",
            jumin_front="681130",
            address="수원시 팔달구 인계동 384 주공아파트 113-105",
            share=None,
        )

        self.assertIsNotNone(located)
        self.assertEqual((1, 2), located.pages)

    def test_composite_rank_can_be_split_between_table_lines(self):
        text = "7\n(1)근저당권설정\n채권최고액 금4,200,000,000원"

        self.assertTrue(rank_is_supported("7(1)", text))
        self.assertFalse(rank_is_supported("7(2)", text))


if __name__ == "__main__":
    unittest.main()
