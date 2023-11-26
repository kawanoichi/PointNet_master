"""Open3Dで3D点群をメッシュ(ポリゴン)に変換するプログラム.
plyファイルからmeshを生成する.
参考URL
    Open3DとPythonによる実装
    https://tecsingularity.com/open3d/bpa/
    PLYファイルについて
    https://programming-surgeon.com/imageanalysis/ply-python/
実行コマンド
$ make surface_run
"""
import numpy as np
import os
from matplotlib import pyplot as plt
import open3d as o3d
# from sklearn.linear_model import RANSACRegressor
import matplotlib.pyplot as plt
# import cv2

import rotate_coordinate as rotate


SCRIPT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR_PATH = os.path.dirname(SCRIPT_DIR_PATH)
PLY_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "predict_points")


class MakeSurface:
    """点群から表面を作りplyファイルに保存するクラス."""

    def __init__(self, point_file_dir, point_file_name) -> None:
        """コンストラクタ.

        Args:
            point_file (str): 点群ファイル(.npy)
        """
        self.point_file_dir = point_file_dir
        self.point_file_name = point_file_name
        self.groupe = None

        # 表示する点群(散布図)に関する変数
        self.fig = plt.figure()  # 表示するグラフ
        self.fig_vertical = 2  # 縦
        self.fig_horizontal = 3  # 横
        self.graph_num = 1  # 横

        # 26方位ベクトルの作成([x, y, z])
        self.vectors_26 = self.vector_26()

        # 26方位に当てはまった各ベクトルの個数
        self.count_vector_class = None

        # y=1方向のベクトルのインデックスを取得
        y1_vector = np.array([0, 1, 0])
        self.y1_vector_index = np.where(
            np.all(self.vectors_26 == y1_vector, axis=1))

        # x=1方向のベクトルのインデックスを取得
        x1_vector = np.array([1, 0, 0])
        self.x1_vector_index = np.where(
            np.all(self.vectors_26 == x1_vector, axis=1))

        # self.x_max = 0
        # self.x_min = 0
        # self.y_max = 0
        # self.y_min = 0
        # self.z_max = 0
        # self.z_min = 0

    def vector_26(self):
        """26方位ベクトル作成関数."""
        kinds_of_coodinate = [-1, 0, 1]

        # 26方位のベクトル(終点座標)を作成
        vectors_26 = np.array([])
        for x in kinds_of_coodinate:
            for y in kinds_of_coodinate:
                for z in kinds_of_coodinate:
                    if not x == y == z == 0:
                        append_coordinate = np.array([x, y, z])
                        vectors_26 = np.append(
                            vectors_26, append_coordinate, axis=0)
        vectors_26 = vectors_26.reshape(
            (len(kinds_of_coodinate) ^ 3)-1, 3)
        return vectors_26

    def angle_between_vectors(self, vector_a, vector_b):
        """ベクトル間のなす角を求める関数.

        ベクトルAとベクトルBのなす角を求める.

        Args:
            vector_a: ベクトルA
            vector_b: ベクトルB
        Return:
            theta_deg: なす角
        """
        dot_product = np.dot(vector_a, vector_b)
        magnitude_a = np.linalg.norm(vector_a)
        magnitude_b = np.linalg.norm(vector_b)

        cos_theta = dot_product / (magnitude_a * magnitude_b)

        # acosはarccosine関数で、cosの逆関数です。
        theta_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))

        # 弧度法から度数法に変換
        return np.degrees(theta_rad)

    def show_point(self, points, title="None") -> None:
        """点群を表示する関数.

        Args:
            points(np.ndarray): 点群
        """
        ax = self.fig.add_subplot(self.fig_vertical,
                                  self.fig_horizontal,
                                  self.graph_num,
                                  projection='3d')
        self.graph_num += 1

        plt.title(title)
        ax.set(xlabel='x', ylabel='y', zlabel='z')

        ax.scatter(points[:, 0],
                   points[:, 1],
                   points[:, 2],
                   c='b')

    def show_point_2D(self, points, title="None") -> None:
        """点群を表示する関数.

        Args:
            points(np.ndarray): 点群
        """
        ax = self.fig.add_subplot(self.fig_vertical,
                                  self.fig_horizontal,
                                  self.graph_num)
        self.graph_num += 1

        plt.title(title)
        ax.set(xlabel='x', ylabel='y')

        ax.scatter(points[:, 0],
                   points[:, 1],
                   c='b',
                   s=5)

    def show_normals(self, points, normals, title="None") -> None:
        """点群と法線ベクトルを表示する関数.

        Args:
            points(np.ndarray): 点群
        """
        ax = self.fig.add_subplot(self.fig_vertical,
                                  self.fig_horizontal,
                                  self.graph_num,
                                  projection='3d')
        self.graph_num += 1

        plt.title(title)
        ax.set(xlabel='x', ylabel='y', zlabel='z')

        # 点をプロット
        ax.scatter(points[:, 0], points[:, 1],
                   points[:, 2], c='b', marker='o', label='Points')

        # 法線ベクトルをプロット
        scale = 0.1  # 矢印のスケール
        for i in range(len(points)):
            if points[i, 0] < -0.05: # 一部を表示
                ax.quiver(points[i, 0], points[i, 1], points[i, 2],
                            normals[i, 0]*scale, normals[i, 1]*scale, normals[i, 2]*scale, color='r', length=1.0, normalize=True)

    def edit_normals(self, points: np.ndarray, normals=None) -> None:
        """法線ベクトルに関連する関数.

        Args:
            points(np.ndarray): 点群

        Variable:
            self.groupe:
                点群の座標のインデックスに関連して、
                26ベクトルの一番近いベクトルのインデックスを格納
        """
        if normals is None:
            normals = np.asarray(points.normals)

        # グラフの追加
        self.show_normals(points, normals, title="Normals")

        # 似た方角を向いたベクトルをグループ分け
        self.groupe = np.zeros(normals.shape[0])
        for i, normal in enumerate(normals):
            min_theta = 180  # 比較するためのなす角
            for j, vector26 in enumerate(self.vectors_26):
                angle = int(self.angle_between_vectors(normal, vector26))
                if angle < min_theta:
                    self.groupe[i] = j
                    min_theta = angle

        # count_vector_classの作成
        # グループ分けされたベクトルの個数をカウントする
        self.count_vector_class = np.zeros(26)
        for i in range(self.vectors_26.shape[0]):
            self.count_vector_class[i] = \
                np.count_nonzero(self.groupe == i)
        print(f"self.count_vector_class:\n {self.count_vector_class}")

        # 最も多い要素を含むグループの点をグラフに追加
        vector_index = np.argmax(self.count_vector_class)
        max_grope_points = points[np.where(self.groupe == vector_index)]
        self.show_point(max_grope_points, title="points of many vector groupe")
        print(
            f"self.vectors_26[vector_index]: {self.vectors_26[vector_index]}")

        self.show_point_2D(max_grope_points, title="2D")
        
        # ベクトルの符号を逆にしてみる
        # invert_some_normals = normals.copy()
        # invert_some_normals[np.where(self.groupe == vector_index)] *= -1
        # self.show_normals(points, invert_some_normals, title="invert vector")
        
        # 点群の座標は少数なので、座標も1000倍しないとだめ？
        # img = np.zeros((1000, 1000), dtype=np.uint8)

        # # 点群の画像を作成
        # for point in points:
        #     cv2.circle(img, tuple(point), 2, 255, -1)

        return normals

    def main(self) -> None:
        """点群をメッシュ化し、表示する関数."""
        # 点群データの読み込み
        point_path = os.path.join(self.point_file_dir, self.point_file_name)

        # 画像の存在チェック
        if not os.path.isfile(point_path):
            raise FileNotFoundError("No file '%s'" % point_path)

        # 点群データの読み込み
        points = np.load(point_path)

        # self.x_max = max(points[:,0])
        # self.x_min = min(points[:,0])
        # self.y_max = max(points[:,1])
        # self.y_min = min(points[:,1])
        # self.z_max = max(points[:,2])
        # self.z_min = min(points[:,2])

        # グラフの追加
        self.show_point(points, title="Input Point")

        # 飛行機の向きを調整
        points2 = points.copy()
        for i, point in enumerate(points2):
            points2[i] = rotate.rotate_around_x_axis(point, 90, reverse=False)
            points2[i] = rotate.rotate_around_y_axis(point, 90, reverse=False)

        # グラフに追加
        # self.show_point(points2, title="Rotated Input Point")

        # NumPyの配列からPointCloudを作成
        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(points)

        # 法線情報を計算
        point_cloud.estimate_normals()

        # 法線ベクトルの編集
        np_normals = np.asarray(point_cloud.normals)

        # 法線ベクトルの作成・編集
        normals = self.edit_normals(points, np_normals)

        # 点群や法線ベクトルの表示
        plt.show()

        # 座標と法線ベクトルをopen3dの形式に変換
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(points)
        mesh.vertex_normals = o3d.utility.Vector3dVector(np_normals)  # ここに法線ベクトルを入れる
        
        # PLYファイルに保存
        # save_path = os.path.join(PROJECT_DIR_PATH, "ply_data", 'mesh.ply')
        # o3d.io.write_triangle_mesh(save_path, mesh, write_ascii=True)


        """
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(point_cloud)
        o3d.visualization.draw_geometries([point_cloud]) # 点群の表示
        o3d.visualization.draw_geometries([mesh]) # メッシュの表示
        # """


if __name__ == "__main__":
    import time
    start = time.time()

    massages = []
    massages.append(f"SCRIPT_DIR_PATH  : {PLY_DIR_PATH}")
    massages.append(f"PROJECT_DIR_PATH : {PROJECT_DIR_PATH}")
    massages.append(f"PLY_DIR_PATH     : {PLY_DIR_PATH}")

    max_length = max(len(massage) for massage in massages)
    line = "_" * max_length

    # 設定の出力
    print(line)
    for massage in massages:
        print(massage)
    print(line)

    file_name = "e50_p2048_airplane_01png.npy"
    # file_name = "e50_p2048_airplane2_15png.npy"
    # file_name = "e50_p2048_airplane_00png.npy"
    # file_name = "e50_p1024_chair_00png.npy"

    ms = MakeSurface(point_file_dir=PLY_DIR_PATH,
                     point_file_name=file_name)
    ms.main()

    # 処理時間計測用
    execute_time = time.time() - start
    print(f"実行時間: {str(execute_time)[:5]}s")

    print("終了")
