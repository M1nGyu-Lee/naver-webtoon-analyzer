import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import random


class GraphWindow:
    def __init__(self, parent, data):
        self.data = data
        self.vars = []

        self.win = tk.Toplevel(parent)
        self.win.title("그래프 선택")
        self.win.geometry("420x620")

        label = tk.Label(
            self.win,
            text="그래프로 비교할 웹툰을 선택하세요.",
            font=("Segoe UI", 10, "bold"),
        )
        label.pack(pady=10)

        frame = tk.Frame(self.win)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for w in data:
            var = tk.IntVar()
            chk = tk.Checkbutton(
                scroll_frame,
                text=w["title"],
                variable=var,
                anchor="w",
                justify="left",
            )
            chk.pack(anchor="w", padx=4, pady=2)
            self.vars.append(var)

        btn_frame = tk.Frame(self.win)
        btn_frame.pack(pady=10, anchor="e", fill="x")

        ok = tk.Button(btn_frame, text="그래프 보기", command=self.draw_graph)
        ok.pack(side="right", padx=10)
        cancel = tk.Button(btn_frame, text="취소", command=self.win.destroy)
        cancel.pack(side="right")

    def draw_graph(self):
        selected = [self.data[i] for i, var in enumerate(self.vars) if var.get() == 1]
        if not selected:
            return

        titles = [w["title"] for w in selected]
        # 기존 rating이 없으면 recent_rating을 사용(없으면 0)
        ratings = [w.get("rating", w.get("recent_rating", 0.0)) for w in selected]
        ranks = [w["rank"] for w in selected]
        colors = [(random.random(), random.random(), random.random()) for _ in titles]

        # 스타일 통일
        plt.style.use("seaborn-v0_8")
        # 한글 폰트 (Windows 기준)
        plt.rcParams["font.family"] = "Malgun Gothic"
        plt.rcParams["axes.unicode_minus"] = False

        # 평점 비교
        plt.figure("웹툰 평점(대체) 비교", figsize=(8, 4))
        plt.title("선택한 웹툰 평점(대체) 비교")
        plt.bar(titles, ratings, color=colors)
        plt.ylabel("평점(대체)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        # 순위 비교 (숫자가 작을수록 순위가 높으므로 축 반전)
        plt.figure("웹툰 순위 비교", figsize=(8, 4))
        plt.title("선택한 웹툰 순위 비교 (낮을수록 높은 순위)")
        plt.bar(titles, ranks, color=colors)
        plt.ylabel("순위")
        plt.gca().invert_yaxis()
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        # 평점 vs 순위
        plt.figure("평점 vs 순위", figsize=(6, 4))
        plt.title("평점과 순위 관계")
        for i in range(len(titles)):
            plt.plot(
                ["평점", "순위"],
                [ratings[i], ranks[i]],
                label=f"{titles[i]} ({ratings[i]}, {ranks[i]})",
                color=colors[i],
                marker="o",
            )
        plt.ylabel("값")
        plt.legend(fontsize=8)
        plt.tight_layout()

        plt.show()
        self.win.destroy()