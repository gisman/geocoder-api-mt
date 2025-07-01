import csv


class CsvReader:
    ROADBASE_HEADER = [
        "시군구코드",
        "기초구간일련번호",
        "기초번호본번",
        "기초번호부번",
        "도로구간일련번호",
        "시도명",
        "시군구명",
        "읍면동코드",
        "읍면동명",
        "도로명코드",
        "도로명",
        "도로구간시점",
        "도로구간종점",
        "중심점좌표_X",
        "중심점좌표_Y",
        "이동사유코드",
        "변경일시",
        "효력발생일",
    ]

    ADDRESS_HEADER = [
        "도로명관리번호",  # 1: 26 문자 PK1
        "법정동코드",  # 2: 10 문자
        "시도명",  # 3: 40 문자
        "시군구명",  # 4: 40 문자
        "읍면동명",  # 5: 40 문자
        "리명",  # 6: 40 문자
        "산여부",  # 7: 1 문자
        "번지",  # 8: 4 숫자
        "호",  # 9: 4 숫자
        "도로명코드",  # 10: 12 문자 PK2
        "도로명",  # 11: 80 문자
        "지하여부",  # 12: 1 문자 PK3
        "건물본번",  # 13: 5 숫자 PK4
        "건물부번",  # 14: 5 숫자 PK5
        "행정동코드",  # 15: 60 문자
        "행정동명",  # 16: 60 문자
        "기초구역번호(우편번호)",  # 17: 5 문자
        "이전도로명주소",  # 18: 400 문자
        "효력발생일",  # 19: 8 문자
        "공동주택구분",  # 20: 1 문자
        "이동사유코드",  # 21: 2 문자 31:신규,34:수정, 63:폐지
        "건축물대장건물명",  # 22: 400 문자
        "시군구용건물명",  # 23: 400 문자
        "비고",  # 24: 200 문자
    ]

    RELACTED_HEADER = [
        "도로명관리번호",  # 1: 26 문자 PK1
        "법정동코드",  # 2: 10 문자 PK2
        "시도명",  # 3: 40 문자
        "시군구명",  # 4: 40 문자
        "읍면동명",  # 5: 40 문자
        "리명",  # 6: 40 문자
        "산여부",  # 7: 1 문자 PK3
        "번지",  # 8: 4 숫자 PK4
        "호",  # 9: 4 숫자 PK5
        "도로명코드",  # 10: 12 문자
        "지하여부",  # 11: 1 문자
        "건물본번",  # 12: 5 숫자
        "건물부번",  # 13: 5 숫자
        "이동사유코드",  # 14: 2 문자 31:신규,34:수정,63:폐지
    ]

    POSITION_HEADER = [
        "도로명관리번호",  # 1: 26 문자 PK1
        "법정동코드",  # 2: 10 문자
        "시도명",  # 3: 40 문자
        "시군구명",  # 4: 40 문자
        "읍면동명",  # 5: 40 문자
        "리명",  # 6: 40 문자
        "도로명코드",  # 7: 12 문자 PK2
        "도로명",  # 8: 80 문자
        "지하여부",  # 9: 1 문자 PK3
        "건물본번",  # 10: 5 숫자 PK4
        "건물부번",  # 11: 5 숫자 PK5
        "기초구역번호(우편번호)",  # 12: 5 문자
        "효력발생일",  # 13: 8 문자
        "이동사유코드",  # 14: 2 문자
        "출입구일련번호",  # 15: 10 숫자
        "출입구구분",  # 16: 2 문자
        "출입구",  # 17: 유형 2 문자
        "출입구좌표X",  # 18: 17 문자
        "출입구좌표Y",  # 19: 17 문자
    ]

    JIBUN_HEADER = [
        "법정동코드",
        "시도명",
        "시군구명",
        "읍면동명",
        "리명",
        "산여부",
        "지번본번",
        "지번부번",
        "도로명코드",
        "지하여부",
        "건물본번",
        "건물부번",
        "지번일련번호",
        "시도명(영문)",
        "시군구명(영문)",
        "읍면동명(영문)",
        "리명(영문)",
        "이동사유코드",
        "건물관리번호",
        "주소관할읍면동코드",
    ]

    JIBUN_HEADER_OLD = [
        "법정동코드",
        "시도명",
        "시군구명",
        "읍면동명",
        "리명",
        "산여부",
        "지번본번",
        "지번부번",
        "도로명코드",
        "지하여부",
        "건물본번",
        "건물부번",
        "지번일련번호",
        "시도명(영문)",
        "시군구명(영문)",
        "읍면동명(영문)",
        "리명(영문)",
        "이동사유코드",
        "건물관리번호",
        # "주소관할읍면동코드",
    ]

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

    SPOT_HEADER = [
        "사물관리번호",  # 18 문자 PK1
        "사물주소일련번호",  # 18 문자 PK2
        "출입구공간_일련번호",  # 22 숫자
        "시군구코드",  # 5 문자
        "시도명",  # 40 문자
        "시군구명",  # 40 문자
        "읍면동명",  # 80 문자
        "도로명코드",  # 7 문자
        "도로명",  # 160 문자
        "지하여부",  # 1 문자 0:지상, 1(지하)
        "주소본번",  # 5 숫자
        "주소부번",  # 4 숫자
        "행정구역코드",  # 10 문자
        "대표주소여부",  # 1 문자
        "X좌표",  # 14,5 숫자
        "Y좌표",  # 14,5 숫자
        "변경일자",  # 8 문자
        "변경사유코드",  # 1 문자 1:신규, 2:변경, 3:삭제
    ]

    ENTR_HEADER = [
        "시군구코드",  # 1: 5 문자
        "출입구일련번호",  # 2: 10 문자
        "법정동코드",  # 3: 10 문자 PK5(시군구코드(5) + 읍면동코드(3) + 00)
        "시도명",  # 4: 40 문자
        "시군구명",  # 5: 40 문자
        "읍면동명",  # 6: 40 문자
        "도로명코드",  # 7: 12 문자 PK1(시군구코드(5)+도로명번호(7))
        "도로명",  # 8: 80 문자
        "지하여부",  # 9: 1 문자 PK2
        "건물본번",  # 10: 5 숫자 PK3
        "건물부번",  # 11: 5 숫자 PK4
        "건물명",  # 12: 40 문자
        "우편번호",  # 13: 5 문자
        "건물용도분류",  # 14: 100 문자 복수 건물용도가 존재시 콤마(,)로 구분
        "건물군여부",  # 15: 1 문자 0:단독건물, 1:건물군
        "관할행정동",  # 16: 8 문자 * 참고용
        "X좌표",  # 17: 15,6 숫자
        "Y좌표",  # 18: 15,6 숫자
    ]

    def get_map(self, row, header):
        data = {}
        for i, key in enumerate(header):
            data[key] = row[i]

        return data

    def read_csv(self, file_path, header, key_column):
        # 31:신규
        # 34:수정
        # 63:폐지
        data_map = {}
        n = 0
        with open(file_path, "r", encoding="euc-kr", errors="ignore") as file:
            reader = csv.reader(file, delimiter="|")
            try:
                for row in reader:
                    if len(row) < 2:  # No Data
                        break
                    row_map = self.get_map(row, header)
                    if key_column:
                        data_map[row_map[key_column]] = row_map
                    else:
                        n += 1
                        data_map[str(n)] = row_map
            except UnicodeDecodeError:
                pass

        return data_map

    def read_address_csv(self, file_path):
        # row = "41500360320703700004400000|4150036026|경기도|이천시|모가면|양평리|0|1|19|415003207037|양녕로|0|44|0|||17408||20240312|0|31|||".split(
        #     "|"
        # )
        # row_map = self.get_map(row, self.ADDRESS_HEADER)
        # data_map = {}
        # data_map[row_map["도로명관리번호"]] = row_map
        # return data_map

        return self.read_csv(file_path, self.ADDRESS_HEADER, "도로명관리번호")

    def read_related_csv(self, file_path):
        # row = "41500360320703700004400000|4150036026|경기도|이천시|모가면|양평리|0|147|55|415003207037|0|44|0|31".split(
        #     "|"
        # )
        # row_map = self.get_map(row, self.RELACTED_HEADER)
        # data_map = {}
        # data_map[row_map["도로명관리번호"]] = row_map
        # return data_map

        return self.read_csv(file_path, self.RELACTED_HEADER, None)

    def read_position_csv(self, file_path):
        try:
            position_map = self.read_csv(
                file_path, self.POSITION_HEADER, "도로명관리번호"
            )

            for key, item in position_map.items():
                item["출입구좌표X"] = (
                    int(float(item["출입구좌표X"])) if item["출입구좌표X"] else None
                )
                item["출입구좌표Y"] = (
                    int(float(item["출입구좌표Y"])) if item["출입구좌표Y"] else None
                )
        except Exception as e:
            print(e)
            position_map = {}

        return position_map

    def read_entr_csv(self, file_path):
        try:
            position_map = self.read_csv(file_path, self.ENTR_HEADER, None)

            for key, item in position_map.items():
                item["X좌표"] = int(float(item["X좌표"])) if item["X좌표"] else None
                item["Y좌표"] = int(float(item["Y좌표"])) if item["Y좌표"] else None
        except Exception as e:
            print(e)
            position_map = {}

        return position_map

    def iter_jibun_csv(self, reader):
        for row in reader:
            try:
                if len(row) < 2:  # No Data
                    break

                if len(row) < 20:
                    row_map = self.get_map(row, self.JIBUN_HEADER_OLD)
                else:
                    row_map = self.get_map(row, self.JIBUN_HEADER)
                yield row_map
            except UnicodeDecodeError:
                continue

    def iter_roadbase_csv(self, reader):
        for row in reader:
            try:
                if len(row) < 2:  # No Data
                    break
                row_map = self.get_map(row, self.ROADBASE_HEADER)

                row_map.pop("기초구간일련번호")
                row_map.pop("도로구간일련번호")
                row_map.pop("도로구간시점")
                row_map.pop("도로구간종점")
                row_map.pop("이동사유코드")
                row_map.pop("변경일시")

                yield row_map
            except UnicodeDecodeError:
                continue

    def iter_navi_csv(self, reader):
        for row in reader:
            try:
                if len(row) < 2:  # No Data
                    break
                row_map = self.get_map(row, self.NAVI_HEADER)
                row_map["출입구_x좌표"] = (
                    int(float(row_map["출입구_x좌표"]))
                    if row_map["출입구_x좌표"]
                    else None
                )
                row_map["출입구_y좌표"] = (
                    int(float(row_map["출입구_y좌표"]))
                    if row_map["출입구_y좌표"]
                    else None
                )

                yield row_map
            except UnicodeDecodeError:
                continue

    def iter_entr_csv(self, reader):
        for row in reader:
            try:
                if len(row) < 2:  # No Data
                    break
                row_map = self.get_map(row, self.ENTR_HEADER)
                row_map["X좌표"] = (
                    int(float(row_map["X좌표"])) if row_map["X좌표"] else None
                )
                row_map["Y좌표"] = (
                    int(float(row_map["Y좌표"])) if row_map["Y좌표"] else None
                )

                yield row_map
            except UnicodeDecodeError:
                continue

    def iter_spot_csv(self, reader):
        for row in reader:
            try:
                if len(row) < 2:  # No Data
                    break
                row_map = self.get_map(row, self.SPOT_HEADER)
                row_map["X좌표"] = (
                    int(float(row_map["X좌표"])) if row_map["X좌표"] else None
                )
                row_map["Y좌표"] = (
                    int(float(row_map["Y좌표"])) if row_map["Y좌표"] else None
                )

                yield row_map
            except UnicodeDecodeError:
                continue
