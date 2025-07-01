import math
import pyogrio
from shapely.geometry import shape


class ShpReader:
    """
    A class to read shapefiles and extract features.

    usage:
        sr = ShpReader(self.shp_path, encoding="cp949")
        for value, geom in sr:
            print(value, geom)

    """

    CHUNK_SIZE = 10000  # Maximum number of features to read

    def __init__(self, shp_path, encoding="utf-8"):
        self.shp_path = shp_path
        self.encoding = encoding

        self.total_features = pyogrio.read_info(
            self.shp_path, encoding=self.encoding, force_feature_count=True
        )["features"]

    def get_total_features(self):
        """
        Returns the total number of features in the shapefile.
        """
        return self.total_features

    def __iter__(self):
        """
        Returns an iterator over the features in the shapefile.
        """

        chunks = math.ceil(self.total_features / self.CHUNK_SIZE)

        for i in range(chunks):
            skip = i * self.CHUNK_SIZE
            # Adjust max_features for the last chunk if it's smaller than chunk_size
            max_feat = min(self.CHUNK_SIZE, self.total_features - skip)

            if max_feat <= 0:
                break  # No more features to read

            df_chunk = pyogrio.read_dataframe(
                self.shp_path,
                encoding=self.encoding,
                skip_features=skip,
                max_features=max_feat,
            )
            # Process df_chunk
            # print(f"Read chunk {i+1} with {len(df_chunk)} features.")

            for idx in range(len(df_chunk)):
                # 인덱스 기반 접근으로 개별 행 생성
                row_data = df_chunk.iloc[idx]
                yield row_data.to_dict(), row_data.geometry
            # for index, row in df_chunk.iterrows():
            #     # geom = shape(row.geometry)
            #     yield row, row.geometry
            #     # yield row.drop("geometry"), geom
