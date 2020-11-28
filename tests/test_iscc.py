# -*- coding: utf-8 -*-
import os
import json
from io import BytesIO
import pytest
from PIL import Image, ImageFilter, ImageEnhance
import iscc


TESTS_PATH = os.path.dirname(os.path.realpath(__file__))
os.chdir(TESTS_PATH)


TEXT_A = u"""
    Their most significant and usefull property of similarity-preserving
    fingerprints gets lost in the fragmentation of individual, propietary and
    use case specific implementations. The real benefit lies in similarity
    preservation beyond your local data archive on a global scale accross
    vendors.
"""

TEXT_B = u"""
    The most significant and usefull property of similarity-preserving
    fingerprints gets lost in the fragmentation of individual, propietary and
    use case specific implementations. The real benefit lies in similarity
    preservation beyond your local data archive on a global scale accross
    vendors.
"""

TEXT_C = u"""
    A need for open standard fingerprinting. We don´t need the best
    Fingerprinting algorithm just an accessible and widely used one.
"""


def test_test_data():
    with open("test_data.json", encoding="utf-8") as jfile:
        data = json.load(jfile)
        assert type(data) == dict
        for funcname, tests in data.items():
            for testname, testdata in tests.items():
                if not testname.startswith("test_"):
                    continue
                func = getattr(iscc, funcname)
                args = testdata["inputs"]
                if funcname in ["data_chunks"]:
                    testdata["outputs"] = [
                        bytes.fromhex(i.split(":")[1]) for i in testdata["outputs"]
                    ]
                    result = list(func(*args))
                else:
                    result = func(*args)
                expected = testdata["outputs"]

                assert result == expected, "%s %s " % (funcname, args)


def test_meta_id():
    mid1, _, _ = iscc.meta_id("ISCC Content Identifiers")
    assert mid1 == "CCbSJTQquHMj8"

    mid1, _, _ = iscc.meta_id(b"ISCC Content Identifiers")
    assert mid1 == "CCbSJTQquHMj8"

    mid1, title, extra = iscc.meta_id("Die Unendliche Geschichte")
    assert mid1 == "CCWkuc9ZnPtRt"
    assert title == "die unendliche geschichte"
    assert extra == ""
    mid2 = iscc.meta_id(" Die unéndlíche,  Geschichte ")[0]
    assert mid1 != mid2

    mid3 = iscc.meta_id("Die Unentliche Geschichte")[0]
    assert iscc.distance(mid1, mid3) == 11

    mid4 = iscc.meta_id("Geschichte, Die Unendliche")[0]
    assert iscc.distance(mid1, mid4) == 11

    with pytest.raises(UnicodeDecodeError):
        iscc.meta_id(b"\xc3\x28")


def test_meta_id_composite():
    mid1, _, _ = iscc.meta_id("This is some Title", "")
    mid2, _, _ = iscc.meta_id("This is some Title", "And some extra metadata")
    assert iscc.decode(mid1)[:5] == iscc.decode(mid2)[:5]
    assert iscc.decode(mid1)[5:] != iscc.decode(mid2)[5:]


def test_encode():
    digest = bytes.fromhex("f7d3a5b201dc92f7a7")
    code = iscc.encode(digest[:1]) + iscc.encode(digest[1:])
    assert code == "5GcvF7s13LK2L"


def test_decode():
    code = "5GcQF7sC3iY2i"
    digest = iscc.decode(code)
    assert digest.hex() == "f7d6bd587d22a7cb6d"


def test_content_id_text():
    cid_t_np = iscc.content_id_text("")
    assert len(cid_t_np) == 13
    assert cid_t_np == "CT7A4zpmccuEv"
    cid_t_p = iscc.content_id_text("", partial=True)
    assert cid_t_p == "Ct7A4zpmccuEv"
    assert 0 == iscc.distance(cid_t_p, cid_t_np)

    cid_t_a = iscc.content_id_text(TEXT_A)
    cid_t_b = iscc.content_id_text(TEXT_B)
    assert iscc.distance(cid_t_a, cid_t_b) == 2


def test_text_normalize():
    text = "  Iñtërnâtiôn\nàlizætiøn☃💩 –  is a tric\t ky \u00A0 thing!\r"

    normalized = iscc.text_normalize(text)
    assert normalized == "internation alizætiøn☃💩 is a tric ky thing!"

    assert iscc.text_normalize(" ") == ""
    assert iscc.text_normalize("  Hello  World ? ") == "hello world ?"
    assert iscc.text_normalize("Hello\nWorld") == "hello world"


def test_trim_text():
    multibyte_2 = "ü" * 128
    trimmed = iscc.text_trim(multibyte_2, 128)
    assert 64 == len(trimmed)
    assert 128 == len(trimmed.encode("utf-8"))

    multibyte_3 = "驩" * 128
    trimmed = iscc.text_trim(multibyte_3, 128)
    assert 42 == len(trimmed)
    assert 126 == len(trimmed.encode("utf-8"))

    mixed = "Iñtërnâtiônàlizætiøn☃💩" * 6
    trimmed = iscc.text_trim(mixed, 128)
    assert 85 == len(trimmed)
    assert 128 == len(trimmed.encode("utf-8"))


def test_sliding_window():
    assert list(iscc.sliding_window("", width=4)) == [""]
    assert list(iscc.sliding_window("A", width=4)) == ["A"]
    assert list(iscc.sliding_window("Hello", width=4)) == ["Hell", "ello"]
    words = ("lorem", "ipsum", "dolor", "sit", "amet")
    assert list(iscc.sliding_window(words, 2))[0] == ("lorem", "ipsum")


def test_similarity_hash():
    all_zero = 0b0 .to_bytes(8, "big")
    assert iscc.similarity_hash((all_zero, all_zero)) == all_zero

    all_ones = 0b11111111 .to_bytes(1, "big")
    assert iscc.similarity_hash((all_ones, all_ones)) == all_ones

    a = 0b0110 .to_bytes(1, "big")
    b = 0b1100 .to_bytes(1, "big")
    r = 0b1110 .to_bytes(1, "big")
    assert iscc.similarity_hash((a, b)) == r

    a = 0b01101001 .to_bytes(1, "big")
    b = 0b00111000 .to_bytes(1, "big")
    c = 0b11100100 .to_bytes(1, "big")
    r = 0b01101000 .to_bytes(1, "big")
    assert iscc.similarity_hash((a, b, c)) == r

    a = 0b0110100101101001 .to_bytes(2, "big")
    b = 0b0011100000111000 .to_bytes(2, "big")
    c = 0b1110010011100100 .to_bytes(2, "big")
    r = 0b0110100001101000 .to_bytes(2, "big")
    assert iscc.similarity_hash((a, b, c)) == r


def test_hamming_distance():
    a = 0b0001111
    b = 0b1000111
    assert iscc.distance(a, b) == 2

    mid1 = iscc.meta_id("Die Unendliche Geschichte", "von Michael Ende")[0]

    # Change one Character
    mid2 = iscc.meta_id("Die UnXndliche Geschichte", "von Michael Ende")[0]
    assert iscc.distance(mid1, mid2) <= 10

    # Delete one Character
    mid2 = iscc.meta_id("Die nendliche Geschichte", "von Michael Ende")[0]
    assert iscc.distance(mid1, mid2) <= 14

    # Add one Character
    mid2 = iscc.meta_id("Die UnendlicheX Geschichte", "von Michael Ende")[0]
    assert iscc.distance(mid1, mid2) <= 13

    # Add, change, delete
    mid2 = iscc.meta_id("Diex Unandlische Geschiche", "von Michael Ende")[0]
    assert iscc.distance(mid1, mid2) <= 22

    # Change Word order
    mid2 = iscc.meta_id("Unendliche Geschichte, Die", "von Michael Ende")[0]
    assert iscc.distance(mid1, mid2) <= 13

    # Totaly different
    mid2 = iscc.meta_id("Now for something different")[0]
    assert iscc.distance(mid1, mid2) >= 24


def test_content_id_mixed():
    cid_t_1 = iscc.content_id_text("Some Text")
    cid_t_2 = iscc.content_id_text("Another Text")

    cid_m = iscc.content_id_mixed([cid_t_1])
    assert cid_m == "CM3LGMnXJvEbR"

    cid_m = iscc.content_id_mixed([cid_t_1, cid_t_2])
    assert cid_m == "CM3LiRzWqKMaK"

    cid_i = iscc.content_id_image("file_image_lenna.jpg")
    cid_m = iscc.content_id_mixed([cid_t_1, cid_t_2, cid_i])
    assert cid_m == "CM3LG2sn7Znpf"


def test_content_id_image():
    cid_i = iscc.content_id_image("file_image_lenna.jpg")
    assert len(cid_i) == 13
    assert cid_i == "CYmLoqBRgV32u"

    data = BytesIO(open("file_image_lenna.jpg", "rb").read())
    cid_i = iscc.content_id_image(data, partial=True)
    assert len(cid_i) == 13
    assert cid_i == "CimLoqBRgV32u"

    img1 = Image.open("file_image_lenna.jpg")
    img2 = img1.filter(ImageFilter.GaussianBlur(10))
    img3 = ImageEnhance.Brightness(img1).enhance(1.4)
    img4 = ImageEnhance.Contrast(img1).enhance(1.2)

    cid1 = iscc.content_id_image(img1)
    cid2 = iscc.content_id_image(img2)
    cid3 = iscc.content_id_image(img3)
    cid4 = iscc.content_id_image(img4)

    assert iscc.distance(cid1, cid2) == 0
    assert iscc.distance(cid1, cid3) == 2
    assert iscc.distance(cid1, cid4) == 0


def test_pi():
    """Check that PI has expected value on systemcd """
    import math

    assert math.pi == 3.141592653589793


def test_image_normalize():
    assert iscc.image_normalize("file_image_cat.jpg") == [
        [
            25,
            18,
            14,
            15,
            25,
            79,
            91,
            92,
            106,
            68,
            109,
            101,
            99,
            93,
            74,
            69,
            58,
            52,
            52,
            73,
            153,
            159,
            131,
            81,
            95,
            81,
            91,
            78,
            50,
            20,
            24,
            26,
        ],
        [
            19,
            17,
            10,
            11,
            17,
            69,
            108,
            112,
            73,
            80,
            113,
            98,
            107,
            90,
            73,
            76,
            87,
            67,
            44,
            112,
            175,
            161,
            122,
            76,
            98,
            69,
            57,
            73,
            51,
            18,
            20,
            23,
        ],
        [
            15,
            19,
            11,
            9,
            12,
            65,
            142,
            96,
            71,
            97,
            110,
            129,
            122,
            70,
            67,
            69,
            102,
            130,
            124,
            167,
            182,
            169,
            104,
            48,
            89,
            72,
            44,
            62,
            53,
            18,
            19,
            23,
        ],
        [
            14,
            18,
            11,
            7,
            7,
            112,
            201,
            173,
            102,
            94,
            124,
            129,
            94,
            71,
            76,
            77,
            116,
            134,
            155,
            177,
            206,
            178,
            85,
            34,
            70,
            72,
            46,
            44,
            50,
            19,
            18,
            20,
        ],
        [
            14,
            17,
            12,
            6,
            7,
            108,
            189,
            214,
            185,
            98,
            91,
            101,
            87,
            85,
            80,
            83,
            108,
            122,
            138,
            177,
            213,
            188,
            54,
            32,
            36,
            50,
            49,
            36,
            41,
            20,
            17,
            20,
        ],
        [
            17,
            20,
            12,
            6,
            8,
            89,
            186,
            213,
            207,
            173,
            80,
            83,
            93,
            90,
            73,
            95,
            112,
            96,
            80,
            126,
            182,
            175,
            47,
            28,
            36,
            26,
            37,
            43,
            43,
            22,
            18,
            21,
        ],
        [
            19,
            20,
            14,
            7,
            7,
            70,
            181,
            223,
            209,
            190,
            149,
            116,
            121,
            99,
            72,
            86,
            122,
            99,
            106,
            122,
            118,
            127,
            63,
            22,
            38,
            32,
            29,
            47,
            49,
            24,
            18,
            21,
        ],
        [
            19,
            22,
            17,
            8,
            7,
            63,
            144,
            221,
            224,
            207,
            177,
            130,
            131,
            89,
            98,
            75,
            100,
            123,
            124,
            131,
            129,
            90,
            54,
            18,
            33,
            45,
            33,
            48,
            44,
            24,
            19,
            21,
        ],
        [
            20,
            23,
            18,
            10,
            6,
            53,
            97,
            194,
            221,
            216,
            200,
            154,
            130,
            112,
            100,
            93,
            104,
            144,
            129,
            107,
            106,
            70,
            45,
            22,
            26,
            40,
            34,
            51,
            41,
            23,
            21,
            22,
        ],
        [
            21,
            24,
            19,
            10,
            5,
            44,
            98,
            179,
            215,
            221,
            189,
            152,
            155,
            124,
            116,
            103,
            110,
            147,
            146,
            136,
            106,
            81,
            53,
            23,
            27,
            28,
            36,
            52,
            38,
            23,
            21,
            22,
        ],
        [
            23,
            25,
            21,
            12,
            4,
            28,
            104,
            162,
            197,
            208,
            191,
            180,
            170,
            140,
            134,
            120,
            106,
            139,
            125,
            133,
            115,
            88,
            62,
            23,
            37,
            44,
            39,
            56,
            37,
            25,
            24,
            24,
        ],
        [
            23,
            25,
            21,
            13,
            5,
            16,
            88,
            113,
            158,
            189,
            183,
            169,
            167,
            154,
            129,
            124,
            133,
            127,
            160,
            156,
            120,
            107,
            72,
            28,
            36,
            41,
            48,
            60,
            40,
            29,
            28,
            28,
        ],
        [
            24,
            25,
            20,
            15,
            8,
            6,
            76,
            128,
            161,
            172,
            176,
            153,
            168,
            169,
            134,
            94,
            155,
            126,
            115,
            98,
            103,
            84,
            75,
            32,
            32,
            40,
            50,
            72,
            42,
            31,
            30,
            30,
        ],
        [
            26,
            23,
            19,
            16,
            12,
            3,
            55,
            131,
            164,
            163,
            185,
            191,
            182,
            175,
            168,
            129,
            150,
            132,
            65,
            126,
            134,
            82,
            50,
            35,
            33,
            47,
            56,
            72,
            38,
            30,
            29,
            29,
        ],
        [
            26,
            23,
            20,
            18,
            17,
            10,
            30,
            128,
            167,
            181,
            195,
            176,
            147,
            208,
            182,
            158,
            130,
            108,
            141,
            128,
            157,
            109,
            87,
            34,
            33,
            45,
            57,
            49,
            32,
            29,
            29,
            31,
        ],
        [
            25,
            23,
            20,
            19,
            20,
            20,
            23,
            108,
            175,
            168,
            168,
            203,
            148,
            202,
            223,
            166,
            128,
            75,
            84,
            133,
            145,
            114,
            81,
            34,
            40,
            53,
            44,
            30,
            31,
            33,
            32,
            34,
        ],
        [
            25,
            22,
            20,
            24,
            28,
            26,
            20,
            81,
            146,
            134,
            210,
            162,
            199,
            151,
            225,
            175,
            129,
            91,
            137,
            173,
            103,
            82,
            57,
            39,
            56,
            62,
            33,
            27,
            37,
            40,
            35,
            36,
        ],
        [
            25,
            24,
            26,
            27,
            34,
            39,
            22,
            32,
            142,
            207,
            194,
            185,
            134,
            151,
            216,
            202,
            130,
            69,
            145,
            125,
            104,
            98,
            67,
            57,
            71,
            55,
            38,
            39,
            37,
            37,
            39,
            39,
        ],
        [
            27,
            27,
            28,
            26,
            31,
            41,
            40,
            27,
            94,
            207,
            212,
            162,
            179,
            201,
            159,
            211,
            140,
            49,
            100,
            125,
            116,
            86,
            75,
            69,
            56,
            40,
            41,
            35,
            36,
            40,
            40,
            43,
        ],
        [
            29,
            28,
            31,
            28,
            30,
            37,
            43,
            44,
            65,
            138,
            202,
            194,
            167,
            176,
            136,
            196,
            157,
            59,
            99,
            111,
            113,
            91,
            81,
            54,
            21,
            24,
            34,
            41,
            40,
            44,
            42,
            44,
        ],
        [
            27,
            28,
            37,
            30,
            30,
            35,
            37,
            44,
            39,
            101,
            199,
            223,
            216,
            209,
            183,
            181,
            173,
            87,
            111,
            131,
            125,
            109,
            101,
            49,
            26,
            30,
            35,
            42,
            44,
            47,
            45,
            46,
        ],
        [
            27,
            28,
            36,
            32,
            34,
            36,
            33,
            36,
            39,
            118,
            233,
            232,
            241,
            212,
            227,
            180,
            119,
            150,
            139,
            142,
            146,
            142,
            131,
            60,
            49,
            50,
            44,
            43,
            46,
            48,
            47,
            47,
        ],
        [
            30,
            36,
            34,
            41,
            43,
            45,
            44,
            56,
            61,
            104,
            241,
            250,
            249,
            231,
            239,
            224,
            139,
            197,
            157,
            164,
            171,
            177,
            153,
            48,
            42,
            56,
            60,
            58,
            53,
            46,
            47,
            48,
        ],
        [
            36,
            46,
            34,
            40,
            53,
            58,
            61,
            54,
            63,
            105,
            219,
            254,
            242,
            241,
            240,
            215,
            170,
            178,
            174,
            214,
            208,
            196,
            167,
            68,
            45,
            58,
            52,
            46,
            48,
            45,
            46,
            49,
        ],
        [
            47,
            52,
            39,
            40,
            47,
            54,
            63,
            75,
            99,
            104,
            137,
            209,
            200,
            182,
            220,
            215,
            180,
            109,
            123,
            242,
            236,
            214,
            163,
            60,
            59,
            49,
            62,
            55,
            50,
            44,
            47,
            50,
        ],
        [
            59,
            52,
            42,
            38,
            52,
            63,
            70,
            98,
            95,
            82,
            72,
            110,
            122,
            105,
            121,
            121,
            94,
            50,
            68,
            220,
            249,
            216,
            127,
            67,
            60,
            55,
            42,
            58,
            57,
            41,
            46,
            54,
        ],
        [
            67,
            62,
            54,
            33,
            67,
            87,
            82,
            92,
            79,
            70,
            61,
            102,
            90,
            82,
            73,
            72,
            71,
            57,
            41,
            110,
            187,
            133,
            88,
            81,
            68,
            57,
            48,
            58,
            65,
            46,
            45,
            53,
        ],
        [
            73,
            72,
            52,
            37,
            81,
            87,
            85,
            88,
            64,
            70,
            76,
            87,
            81,
            75,
            75,
            75,
            79,
            68,
            51,
            55,
            69,
            51,
            73,
            79,
            76,
            57,
            62,
            55,
            65,
            55,
            46,
            52,
        ],
        [
            78,
            72,
            41,
            51,
            78,
            74,
            91,
            85,
            54,
            78,
            91,
            72,
            84,
            74,
            76,
            73,
            77,
            75,
            59,
            57,
            66,
            50,
            66,
            75,
            62,
            57,
            69,
            63,
            55,
            61,
            54,
            51,
        ],
        [
            73,
            71,
            56,
            66,
            69,
            77,
            88,
            77,
            57,
            82,
            97,
            68,
            81,
            74,
            72,
            74,
            77,
            66,
            64,
            61,
            65,
            54,
            66,
            69,
            60,
            59,
            61,
            71,
            54,
            64,
            51,
            55,
        ],
        [
            70,
            68,
            64,
            67,
            67,
            71,
            79,
            68,
            66,
            82,
            87,
            69,
            78,
            73,
            73,
            73,
            76,
            66,
            62,
            68,
            66,
            58,
            67,
            62,
            64,
            60,
            62,
            62,
            55,
            64,
            49,
            52,
        ],
        [
            77,
            69,
            64,
            70,
            64,
            68,
            70,
            72,
            73,
            84,
            76,
            72,
            78,
            78,
            75,
            73,
            77,
            67,
            67,
            65,
            71,
            59,
            65,
            66,
            66,
            65,
            61,
            65,
            54,
            62,
            50,
            52,
        ],
    ]
