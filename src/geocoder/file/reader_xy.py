import pandas as pd

from src.geocoder.file.reader import Reader


class ReaderXY(Reader):
    def __init__(
        self, filepath, charenc, delimiter, x_col, y_col, start_row=0, row_count=-1
    ):
        self.filepath = filepath
        self.charenc = charenc
        self.delimiter = delimiter
        self.address_col = -1
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

        self.x_col = self.headers.index(x_col)
        self.y_col = self.headers.index(y_col)

        # x_col, y_col이 유효한지 확인
        if self.x_col > -1 and self.x_col >= len(self.headers):
            raise ValueError(
                f"x_col({self.x_col})이 헤더 개수({len(self.headers)})를 초과합니다."
            )
        if self.y_col > -1 and self.y_col >= len(self.headers):
            raise ValueError(
                f"y_col({self.y_col})이 헤더 개수({len(self.headers)})를 초과합니다."
            )

    def __next__(self):
        if self.current_index >= len(self.df):
            raise StopIteration

        # 현재 행 데이터 가져오기
        row = self.df.iloc[self.current_index]
        line = row.tolist()

        # X, Y 컬럼 데이터 가져오기
        if self.x_col < len(line):
            x = str(line[self.x_col]).strip()
            y = str(line[self.y_col]).strip()
        else:
            x = y = ""

        self.current_index += 1
        return line, (x, y)

    def get_row_count(self):
        """총 행 수 반환"""
        return len(self.df)
