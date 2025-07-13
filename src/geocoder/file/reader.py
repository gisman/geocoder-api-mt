import pandas as pd


class Reader:
    def __init__(
        self, filepath, charenc, delimiter, address_col, start_row=0, row_count=-1
    ):
        self.filepath = filepath
        self.charenc = charenc
        self.delimiter = delimiter
        self.address_col = address_col
        self.start_row = start_row
        self.row_count = row_count

        # pandas를 사용하여 CSV 파일 읽기
        try:
            # 전체 파일을 읽거나 지정된 행 수만큼 읽기
            if row_count > 0:
                self.df = pd.read_csv(
                    filepath,
                    encoding=charenc,
                    encoding_errors="ignore",  # 유니코드 오류 무시
                    delimiter=delimiter,
                    quotechar='"',  # 쌍따옴표를 사용하여 콤마 포함된 값을 처리
                    escapechar="\\",
                    skiprows=start_row,
                    nrows=row_count,
                    dtype=str,  # 모든 컬럼을 문자열로 읽기
                    na_filter=False,  # NaN 값을 빈 문자열로 처리
                )
            else:
                self.df = pd.read_csv(
                    filepath,
                    encoding=charenc,
                    encoding_errors="ignore",  # 유니코드 오류 무시
                    delimiter=delimiter,
                    quotechar='"',  # 쌍따옴표를 사용하여 콤마 포함된 값을 처리
                    escapechar="\\",
                    skiprows=start_row,
                    dtype=str,
                    na_filter=False,
                )
        except Exception as e:
            raise ValueError(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")

        self.headers = list(self.df.columns)
        self.current_index = 0

        # address_col이 유효한지 확인
        if address_col >= len(self.headers):
            raise ValueError(
                f"address_col({address_col})이 헤더 개수({len(self.headers)})를 초과합니다."
            )

    def get_headers(self):
        return self.headers

    def __iter__(self):
        self.current_index = 0
        return self

    def __next__(self):
        if self.current_index >= len(self.df):
            raise StopIteration

        # 현재 행 데이터 가져오기
        row = self.df.iloc[self.current_index]
        line = row.tolist()

        # 주소 컬럼 데이터 가져오기
        if self.address_col < len(line):
            addr = str(line[self.address_col]).strip()
        else:
            addr = ""

        self.current_index += 1
        return line, addr

    def get_data_frame(self):
        """전체 DataFrame 반환 (pandas 활용을 위한 추가 메서드)"""
        return self.df

    def get_address_column_data(self):
        """주소 컬럼 데이터만 반환"""
        if self.address_col < len(self.headers):
            return self.df.iloc[:, self.address_col].tolist()
        return []

    def get_row_count(self):
        """총 행 수 반환"""
        return len(self.df)

    def __str__(self):
        return f"Reader(rows={len(self.df)}, columns={len(self.headers)})"

    def count(self):
        """총 행 수 반환"""
        return len(self.df)
