# enc
import chardet
from chardet.universaldetector import UniversalDetector


class Enc:
    def __init__(self, filename):
        self.filename = filename

    def detect_delimiter(self, charenc):
        try:
            with open(self.filename, "r", encoding=charenc) as f:
                s = f.readline()
                if str(s).count("Unnamed:") > 2:
                    s = f.readline()
            f.close()
            # s = s.decode(charenc)
            delimeters = [",", "|", ":", "=", "\t", ";", "!", "=", "%", "&", "*", "#"]

            cnts = list(map(lambda d: s.count(d), delimeters))
            max_value = max(cnts)

            return delimeters[cnts.index(max_value)]
        except Exception as e:
            return ","

    def detect_enc(self):
        try:
            detector = UniversalDetector()
            TEST_LIMIT, linecount = 50, 0
            with open(self.filename, "rb") as f:
                while linecount < TEST_LIMIT:
                    line = f.readline()
                    linecount += 1
                    detector.feed(line)
                    if detector.done:
                        break

            detector.close()
            f.close()
            charenc = detector.result["encoding"]
            if charenc and not charenc.lower().startswith("utf"):
                if charenc != "Windows-1252":
                    charenc = "cp949"
            return charenc
            # f = open(self..filename, 'rb')

            # for line in f.readlines():
            #     detector.feed(line)
            #     if detector.done:
            #         break

            # detector.close()
            # f.close()

            # return detector.result['encoding']
        except Exception as e:
            return None

    def run(self):
        if not self._context.fileext in (".CSV", ".JSON", ".XML", ".TXT"):
            return None

        charenc = self.detect_enc()
        delimiter = self.detect_delimiter(charenc)

        # encoding detection 실패시 cp949로 강제 설정
        if charenc and not charenc.lower().startswith("utf"):
            charenc = "cp949"

        self.put("encoding", charenc)
        self.put("delimiter", delimiter)

        self._context.notebook.add_code(f"charenc = '{charenc}'")
        self._context.notebook.add_md(
            f"""## Character Encoding
{charenc}
"""
        )

        self._context.add_desciption(f"* 인코딩: {charenc}\n")
        return charenc
