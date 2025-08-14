import csv
import os

X_AXIS = "x_axis"
Y_AXIS = "y_axis"


class Writer:
    def __init__(
        self,
        filepath,
        headers,
        charenc="utf-8",
        delimiter=",",
        hd_history_cols=[],
    ):
        # self.filepath = filepath
        self.charenc = charenc
        self.delimiter = delimiter
        self.headers = headers
        self.fieldnames = (
            headers
            + [
                "success",
                X_AXIS,
                Y_AXIS,
                "h1_cd",
                "h2_cd",
                "kostat_h1_cd",
                "kostat_h2_cd",
                "hd_cd",
                "hd_nm",
                "pos_cd",
                "errmsg",
                "hash",
                "toksString",
                "inputaddr",
            ]
            + hd_history_cols
        )

        filename = os.path.basename(filepath)
        self.csvfile = open(filepath, "w", newline="")
        self.csv_writer = csv.DictWriter(
            self.csvfile,
            fieldnames=self.fieldnames,
            delimiter=delimiter,
        )

    def write(self, input_line, row_result):
        # make dict from line(list) as values and headers as keys
        prefix = dict(zip(self.headers, input_line))

        row_out = {
            "success": row_result["success"],
            X_AXIS: row_result[X_AXIS],
            Y_AXIS: row_result[Y_AXIS],
            "h1_cd": row_result["h1_cd"],
            "h2_cd": row_result["h2_cd"],
            "kostat_h1_cd": row_result["kostat_h1_cd"],
            "kostat_h2_cd": row_result["kostat_h2_cd"],
            "hd_cd": row_result.get("hd_cd") or "",
            "hd_nm": row_result.get("hd_nm") or "",
            "pos_cd": row_result.get("pos_cd") or "",
            "errmsg": row_result.get("errmsg") or "",
            "hash": row_result.get("hash") or "",
            "toksString": row_result.get("toksString") or "",
            "inputaddr": row_result.get("inputaddr") or "",
        }

        if "hd_history" in row_result:
            # add history_list to row_out
            for history in row_result["hd_history"]:
                row_out[f'hd_cd_{history["yyyymm"]}'] = history["EMD_CD"]
                row_out[f'hd_nm_{history["yyyymm"]}'] = history["EMD_KOR_NM"]

        # merge prefix and row
        row_out.update(prefix)

        # Remove keys from row_out that are not in self.csv_writer.fieldnames
        row_out = {
            key: value
            for key, value in row_out.items()
            if key in self.csv_writer.fieldnames
        }
        self.csv_writer.writerow(row_out)

    def writeheader(self):
        self.csv_writer.writeheader()
