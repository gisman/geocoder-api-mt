import glob
import pandas as pd
import config

JUSO_DATA_DIR = config.JUSO_DATA_DIR

NAVI_HEADER = [
    "주소관할읍면동코드",
    "시도명",
    "시군구명",
    "읍면동명",
    "도로명코드",
    "도로명",
    "지하여부",
    "건물본번",
    "건물부번",
    "우편번호",
    "건물관리번호",
    "시군구용건물명",
    "건축물용도분류",
    "행정동코드",
    "행정동명",
    "지상층수",
    "지하층수",
    "공동주택구분",
    "건물수",
    "상세건물명",
    "건물명변경이력",
    "상세건물명변경이력",
    "거주여부",
    "건물중심점_x좌표",
    "건물중심점_y좌표",
    "출입구_x좌표",
    "출입구_y좌표",
    "시도명(영문)",
    "시군구명(영문)",
    "읍면동명(영문)",
    "도로명(영문)",
    "읍면동구분",
    "이동사유코드",
]


def merge_test():
    df_match = pd.DataFrame(
        {
            "시도명": ["인천광역시", "인천광역시"],
            "시군구명": ["남구", "계양구"],
            "시도코드": ["11", "11"],
            "시군구코드": ["1111", "1122"],
        }
    )

    df1 = pd.DataFrame(
        {
            "시도명": ["인천광역시", "인천광역시"],
            "시군구명": ["미추홀구", "계양구"],
            "시도코드": ["11", "11"],
            "시군구코드": ["1133", "1122"],
        }
    )

    df_match = df_match.merge(df1, on=["시도명", "시군구명"], how="outer")
    df_match = df_match.sort_values(by=["시도명", "시군구명"])

    df_match.loc[df_match["시도코드_y"].notna(), "시도코드"] = df_match["시도코드_y"]
    df_match.loc[df_match["시군구코드_y"].notna(), "시군구코드"] = df_match[
        "시군구코드_y"
    ]
    df_match.loc[df_match["시도코드_x"].notna(), "시도코드"] = df_match["시도코드_x"]
    df_match.loc[df_match["시군구코드_x"].notna(), "시군구코드"] = df_match[
        "시군구코드_x"
    ]
    df_match.drop(
        columns=["시도코드_x", "시군구코드_x", "시도코드_y", "시군구코드_y"],
        inplace=True,
    )
    # df_match.rename(
    #     columns={"시도코드_x": "시도코드", "시군구코드_x": "시군구코드"},
    #     inplace=True,
    # )
    df_match = df_match[
        ["시도명", "시군구명", "시도코드", "시군구코드"]
    ].drop_duplicates()

    print(df_match.to_string())


df_match = None


def match(filename):
    """
    Matches and updates the code matching table based on the given filename.

    Args:
        filename (str): The path to the file containing the data to be matched.

    Returns:
        None
    """

    global df_match

    df = pd.read_csv(
        filename,
        delimiter="|",
        encoding="euc-kr",
        on_bad_lines="skip",
        encoding_errors="ignore",
        names=NAVI_HEADER,
        dtype=str,
    )
    df = df.dropna(subset=["행정동코드"])
    # df = df.dropna(subset=["주소관할읍면동코드"])
    df = df[df["이동사유코드"] != "63"]

    df["시도코드"] = df["행정동코드"].str[:2]
    df["시군구코드"] = df["행정동코드"].str[:5]
    # get distinct "시도명", "시군구명", "행정동코드[:5] from df
    df1 = df[["시도명", "시군구명", "시도코드", "시군구코드"]].drop_duplicates()

    # print(df1)
    if df_match is None:
        df_match = df1
    else:
        df_match = df_match.merge(df1, on=["시도명", "시군구명"], how="outer")
        df_match = df_match.sort_values(by=["시도명", "시군구명"])

        df_match.loc[df_match["시도코드_y"].notna(), "시도코드"] = df_match[
            "시도코드_y"
        ]
        df_match.loc[df_match["시군구코드_y"].notna(), "시군구코드"] = df_match[
            "시군구코드_y"
        ]
        df_match.loc[df_match["시도코드_x"].notna(), "시도코드"] = df_match[
            "시도코드_x"
        ]
        df_match.loc[df_match["시군구코드_x"].notna(), "시군구코드"] = df_match[
            "시군구코드_x"
        ]

        df_match.drop(
            columns=["시도코드_x", "시군구코드_x", "시도코드_y", "시군구코드_y"],
            inplace=True,
        )
        # df_match.rename(
        #     columns={"시도코드_x": "시도코드", "시군구코드_x": "시군구코드"},
        #     inplace=True,
        # )
        df_match = df_match[
            ["시도명", "시군구명", "시도코드", "시군구코드"]
        ].drop_duplicates()

        # print(df_match.to_string())


if __name__ == "__main__":
    # from sys import argv

    # merge_test()
    # exit(0)

    # 월 변동분, 과거에서 현재 순
    # /home/gisman/projects/geocoder-api/juso-data/월변동분/NAVI/*/match_build_mod.txt
    pattern = f"{JUSO_DATA_DIR}/월변동분/NAVI/*/match_build_mod.txt"

    for filename in sorted(glob.glob(pattern)):
        print("월 변동분", filename)
        # h1, h2 같은 것이 있으면 최신 행정동 코드를 변경

        match(filename)

    # 전체분
    # /home/gisman/projects/geocoder-api/juso-data/전체분/navi/match_build_*.txt
    pattern = f"{JUSO_DATA_DIR}/전체분/navi/match_build_*.txt"

    for filename in glob.glob(pattern):
        print("전체분", filename)

        match(filename)

    df_match.to_csv("/home/gisman/projects/geocoder-api/h1_h2_code.csv", index=False)

    # dic
    # key = h2
    # val = h1_nm, h2_nm, h1_cd, h2_cd
    # 향후 행정동, 법정동 매칭 테이블도 제작
