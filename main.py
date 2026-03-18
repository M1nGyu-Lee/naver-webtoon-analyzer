import tkinter as tk
from tkinter import ttk
import webbrowser
import requests
from PIL import Image, ImageTk
from io import BytesIO
import json
import threading
import queue
import subprocess
import sys

from crawler import HEADERS
from graph_window import GraphWindow

class App:
    CARD_WIDTH = 180
    CARD_HEIGHT = 260

    def __init__(self, root):
        self.root = root
        root.title("NAVER Webtoon Analyzer")
        # 가로 1080, 세로 760, 화면 왼쪽에서 200px, 위에서 10px 위치
        root.geometry("1080x760+200+10")
        # 라이트 모드 기본 배경을 더 차분한 회청색으로
        root.configure(bg="#e5e7eb")

        self.data = []
        self.all_data = []
        self.images = {}  # 카드별 PhotoImage 참조
        self.image_cache = {}  # 썸네일 URL별 PhotoImage 캐시
        self.thumb_refs = {}  # 라벨별 PhotoImage 참조(가비지 컬렉션 방지)
        self._thumb_queue = queue.Queue()
        self._thumb_worker = None
        self._thumb_cancel = threading.Event()
        self.status_var = tk.StringVar(value="웹툰 데이터를 불러오는 중입니다...")
        self.tooltip = None
        self.search_var = tk.StringVar()
        self.genre_var = tk.StringVar(value="전체")
        self.theme = tk.StringVar(value="light")  # light / dark

        style = ttk.Style()
        style.theme_use("clam")

        # 버튼 스타일 (초록 계열, 모서리 둥근 느낌의 타원 기둥)
        style.configure(
            "Big.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 6),
            background="#00c853",
            foreground="#ffffff",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Big.TButton",
            background=[("active", "#00a94f"), ("pressed", "#009846")],
            foreground=[("disabled", "#d1d5db")],
        )

        # 상단 타이틀 영역
        self.header_frame = tk.Frame(root, bg="#e5e7eb", padx=0, pady=0)
        self.header_frame.pack(fill="x")

        self.title_label = tk.Label(
            self.header_frame,
            text="NAVER Webtoon Analyzer",
            font=("Segoe UI", 16, "bold"),
            bg="#e5e7eb",
            fg="#111827",
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = tk.Label(
            self.header_frame,
            text="네이버 웹툰 메타데이터를 수집해 카드 형태로 탐색·분석합니다.",
            font=("Segoe UI", 10),
            bg="#e5e7eb",
            fg="#6b7280",
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        # 검색 / 장르 필터 영역
        self.filter_frame = tk.Frame(self.header_frame, bg="#e5e7eb")
        self.filter_frame.pack(anchor="w", pady=(4, 4), fill="x")

        self.search_label = tk.Label(
            self.filter_frame,
            text="제목 검색",
            font=("Segoe UI", 9),
            bg="#e5e7eb",
            fg="#4b5563",
        )
        self.search_label.pack(side="left", padx=(0, 4))

        self.search_entry = tk.Entry(
            self.filter_frame, textvariable=self.search_var, width=30, font=("Segoe UI", 9)
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.apply_filters())

        self.tag_label = tk.Label(
            self.filter_frame,
            text="   태그",
            font=("Segoe UI", 9),
            bg="#e5e7eb",
            fg="#4b5563",
        )
        self.tag_label.pack(side="left", padx=(12, 4))
        self.genre_combo = ttk.Combobox(
            self.filter_frame,
            textvariable=self.genre_var,
            state="readonly",
            width=18,
            font=("Segoe UI", 9),
            values=["전체"],
        )
        self.genre_combo.current(0)
        self.genre_combo.pack(side="left")

        ttk.Button(
            self.filter_frame,
            text="필터 적용",
            command=self.apply_filters,
            style="Big.TButton",
        ).pack(side="left", padx=8)

        ttk.Button(
            self.filter_frame,
            text="초기화",
            command=self.reset_filters,
            style="Big.TButton",
        ).pack(side="left", padx=4)

        ttk.Button(
            self.filter_frame,
            text="테마 전환",
            command=self.toggle_theme,
            style="Big.TButton",
        ).pack(side="right", padx=4)

        self.main_frame = tk.Frame(root, padx=0, pady=0, bg="#e5e7eb")
        self.main_frame.pack(fill="both", expand=True)

        # 카드 그리드를 위한 캔버스 + 스크롤
        self.canvas = tk.Canvas(self.main_frame, bg="#e5e7eb", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.cards_frame = tk.Frame(self.canvas, bg="#e5e7eb")
        self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cards_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        # 마우스 휠로도 스크롤 가능하게 설정
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.btn_frame = tk.Frame(root, pady=8, padx=12, bg="#e5e7eb")
        self.btn_frame.pack(side="bottom", fill="x")

        ttk.Button(
            self.btn_frame,
            text="선택 웹툰 그래프",
            command=self.open_graph,
            style="Big.TButton",
        ).pack(side="left", padx=5)

        ttk.Button(
            self.btn_frame,
            text="상/하위 랭크 그래프",
            command=self.open_rank_plot,
            style="Big.TButton",
        ).pack(side="left", padx=5)

        status_label = tk.Label(
            self.btn_frame,
            textvariable=self.status_var,
            anchor="e",
            font=("Segoe UI", 9),
            bg="#e5e7eb",
            fg="#6b7280",
        )
        status_label.pack(side="right", padx=5)

        # 로컬 데이터 로드
        self.root.after(150, self.load_data)

    def load_data(self):
        # 로딩 상태 표시
        self.status_var.set("웹툰 데이터를 불러오는 중입니다...")
        self.root.config(cursor="watch")
        self.root.update_idletasks()

        # export_webtoons.py로 미리 저장한 webtoons.json 읽기
        try:
            with open("webtoons.json", "r", encoding="utf-8") as f:
                self.all_data = json.load(f)
        except FileNotFoundError:
            self.all_data = []
            self.status_var.set("webtoons.json 파일이 없습니다. 먼저 export_webtoons.py를 실행해서 데이터를 생성하세요.")
            self.root.config(cursor="")
            return
        except Exception:
            self.all_data = []
            self.status_var.set("webtoons.json 파일을 읽는 중 오류가 발생했습니다.")
            self.root.config(cursor="")
            return

        # 장르(태그) 목록 추출해서 콤보박스에 반영
        genres = set()
        for w in self.all_data:
            for tag in w.get("tags") or []:
                genres.add(tag)
        genre_list = ["전체"] + sorted(genres)
        self.genre_combo.configure(values=genre_list)
        self.genre_var.set("전체")

        self.apply_filters()

    def reset_filters(self):
        self.search_var.set("")
        self.genre_var.set("전체")
        # 콤보박스 UI도 '전체'로 맞춰주기
        try:
            self.genre_combo.current(0)
        except Exception:
            pass
        self.apply_filters()

    def apply_filters(self):
        # 진행 중인 썸네일 로더가 있으면 중단
        self._cancel_thumbnail_loading()

        # 기존 카드 제거
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.images.clear()
        self.thumb_refs.clear()

        if not self.all_data:
            self.status_var.set("웹툰 데이터를 불러오지 못했습니다.")
            self.root.config(cursor="")
            return

        keyword = self.search_var.get().strip().lower()
        selected_genre = self.genre_var.get()

        # 필터 적용
        filtered = []
        for w in self.all_data:
            title = w["title"]
            tags = w.get("tags") or []

            if keyword and keyword not in title.lower():
                continue
            if selected_genre != "전체" and selected_genre not in tags:
                continue
            filtered.append(w)

        # 최근 평균 별점 기준 내림차순, 그다음 rank 기준 정렬
        filtered.sort(
            key=lambda x: (-float(x.get("recent_rating", 0.0)), x.get("rank", 0))
        )
        self.data = filtered

        # 카드 그리드 배치
        max_width = self.canvas.winfo_width() or 1000
        cards_per_row = max(1, max_width // (self.CARD_WIDTH + 16))

        # 로딩 오버레이 준비
        self._show_loading_overlay(total=len(self.data))

        # 썸네일 로딩 대상 수집 (캐시된 것은 바로 적용)
        to_download = []

        for idx, w in enumerate(self.data):
            row = idx // cards_per_row
            col = idx % cards_per_row

            card = tk.Frame(
                self.cards_frame,
                width=self.CARD_WIDTH,
                height=self.CARD_HEIGHT,
                bg=self._card_bg(),
                highlightthickness=0 if self.theme.get() == "dark" else 1,
                highlightbackground=self._card_bg() if self.theme.get() == "dark" else "#e5e7eb",
            )
            card.grid(row=row, column=col, padx=8, pady=8)
            card.grid_propagate(False)

            # 썸네일
            thumbnail_url = w.get("thumbnail")
            photo = self.image_cache.get(thumbnail_url) if thumbnail_url else None
            self.images[w["title"]] = photo

            img_label = tk.Label(
                card,
                bg=self._card_bg(),
                cursor="hand2",
                text="" if photo else "LOADING",
                fg="#9ca3af",
            )
            if photo:
                img_label.configure(image=photo)
                img_label.image = photo
                self.thumb_refs[id(img_label)] = photo
            img_label.pack(pady=(8, 4))

            # 캐시가 없으면 다운로드 대상에 추가
            if thumbnail_url and not photo:
                to_download.append((idx, thumbnail_url, img_label))

            # 제목
            title_label = tk.Label(
                card,
                text=w["title"],
                font=("Segoe UI", 10, "bold"),
                bg=self._card_bg(),
                fg=self._fg(),
                wraplength=self.CARD_WIDTH - 16,
                justify="center",
            )
            title_label.pack(padx=8)

            # 순번만 표시 (#1, #2 ...)
            meta_label = tk.Label(
                card,
                text=f"#{w['rank']}",
                font=("Segoe UI", 9),
                bg=self._card_bg(),
                fg="#6b7280",
            )
            meta_label.pack(pady=(2, 6))

            link = w["link"]
            img_label.bind("<Button-1>", lambda e, url=link: webbrowser.open(url))
            title_label.bind("<Button-1>", lambda e, url=link: webbrowser.open(url))

            # 호버 툴팁 (소개 + 태그)
            tags = w.get("tags") or []
            tag_text = ", ".join(tags) if tags else "태그 없음"
            description = w.get("description") or "소개 정보가 없습니다."
            tooltip_text = f"{description}\n\n태그: {tag_text}"
            for widget in (img_label, title_label, meta_label):
                widget.bind("<Enter>", lambda e, text=tooltip_text: self.show_tooltip(e, text))
                widget.bind("<Leave>", self.hide_tooltip)

        # 썸네일 로딩 시작
        self._start_thumbnail_loading(to_download, total=len(self.data))

    def open_graph(self):
        if not self.data:
            return
        GraphWindow(self.root, self.data)

    def open_rank_plot(self):
        # matplotlib 그래프 스크립트를 별도 프로세스로 실행(메인 UI 블로킹 방지)
        try:
            subprocess.Popen([sys.executable, "analyze_rank_plot.py"])
        except Exception:
            pass

    def show_tooltip(self, event, text: str):
        if self.tooltip:
            self.tooltip.destroy()

        x = event.x_root + 10
        y = event.y_root + 10
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip,
            text=text,
            justify="left",
            font=("Segoe UI", 9),
            bg="#111827",
            fg="#f9fafb",
            padx=8,
            pady=6,
            wraplength=260,
        )
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    # --- 로딩 오버레이 / 썸네일 비동기 로딩 ---

    def _show_loading_overlay(self, total: int):
        # 기존 오버레이 제거
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            try:
                self._loading_overlay.destroy()
            except Exception:
                pass

        self._loading_total = max(1, int(total))
        self._loading_done = 0

        self._loading_overlay = tk.Frame(
            self.root,
            bg="#000000",
        )
        # 약간 투명 느낌을 위해 색만 어둡게(진짜 투명은 Tkinter에서 까다로움)
        self._loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        box = tk.Frame(self._loading_overlay, bg="#111827", padx=16, pady=12)
        box.place(relx=0.5, rely=0.5, anchor="center")

        self._loading_label = tk.Label(
            box,
            text="로딩중 입니다...",
            font=("Segoe UI", 11, "bold"),
            bg="#111827",
            fg="#e5e7eb",
        )
        self._loading_label.pack(anchor="center")

        self._loading_progress = ttk.Progressbar(box, mode="determinate", length=260, maximum=self._loading_total)
        self._loading_progress.pack(pady=(10, 0))

        self._loading_hint = tk.Label(
            box,
            text="썸네일을 불러오는 중입니다.",
            font=("Segoe UI", 9),
            bg="#111827",
            fg="#9ca3af",
        )
        self._loading_hint.pack(pady=(8, 0))

        self.root.config(cursor="watch")

    def _hide_loading_overlay(self):
        try:
            if hasattr(self, "_loading_overlay") and self._loading_overlay:
                self._loading_overlay.destroy()
        except Exception:
            pass
        self._loading_overlay = None
        self.root.config(cursor="")
        self.status_var.set(f"총 {len(self.data)}개 웹툰을 불러왔습니다.")

    def _cancel_thumbnail_loading(self):
        try:
            self._thumb_cancel.set()
        except Exception:
            pass
        self._thumb_cancel = threading.Event()
        # 큐 비우기
        try:
            while True:
                self._thumb_queue.get_nowait()
        except Exception:
            pass

    def _start_thumbnail_loading(self, to_download, total: int):
        # 캐시로 이미 다 있는 경우
        if not to_download:
            self._loading_progress["value"] = self._loading_total
            self._hide_loading_overlay()
            return

        # 워커 스레드: 이미지 bytes만 다운로드해서 큐에 넣기
        def worker():
            for _, url, _label in to_download:
                if self._thumb_cancel.is_set():
                    return
                try:
                    res = requests.get(url, headers=HEADERS, timeout=10)
                    content = res.content
                except Exception:
                    content = None
                self._thumb_queue.put((url, content))

        self._thumb_worker = threading.Thread(target=worker, daemon=True)
        self._thumb_worker.start()

        # 메인 스레드: 큐에서 꺼내 UI 업데이트
        pending_by_url = {}
        for _idx, url, label in to_download:
            pending_by_url.setdefault(url, []).append(label)

        def poll():
            updated = 0
            while True:
                try:
                    url, content = self._thumb_queue.get_nowait()
                except Exception:
                    break

                labels = pending_by_url.get(url, [])
                photo = None
                if content:
                    try:
                        img = Image.open(BytesIO(content))
                        img = img.resize((140, 180))
                        photo = ImageTk.PhotoImage(img)
                        self.image_cache[url] = photo
                    except Exception:
                        photo = None

                for label in labels:
                    if photo:
                        label.configure(image=photo, text="")
                        label.image = photo
                        self.thumb_refs[id(label)] = photo
                    else:
                        label.configure(text="NO IMAGE")

                updated += 1
                self._loading_done += 1

            # 진행률 업데이트
            if hasattr(self, "_loading_progress") and self._loading_progress:
                self._loading_progress["value"] = min(self._loading_done, self._loading_total)

            if self._thumb_cancel.is_set():
                self._hide_loading_overlay()
                return

            # 아직 남았으면 계속 폴링
            if self._loading_done < len(to_download):
                self.root.after(50, poll)
            else:
                # 다운로드 끝
                self._hide_loading_overlay()

        # total은 카드 수 기준이므로, progress는 다운로드 개수 기준으로 maximum 재설정
        self._loading_total = max(1, len(to_download))
        self._loading_progress.configure(maximum=self._loading_total)
        self._loading_progress["value"] = 0
        self._loading_done = 0

        self.root.after(50, poll)

    # --- 테마 관련 헬퍼 ---

    def toggle_theme(self):
        new_theme = "dark" if self.theme.get() == "light" else "light"
        self.theme.set(new_theme)

        if new_theme == "dark":
            bg_root = "#050816"
            bg_panel = "#050816"
            fg_title = "#e5e7eb"
            fg_sub = "#9ca3af"
            entry_bg = "#111827"
            entry_fg = "#e5e7eb"
        else:
            bg_root = "#e5e7eb"
            bg_panel = "#e5e7eb"
            fg_title = "#111827"
            fg_sub = "#6b7280"
            entry_bg = "#ffffff"
            entry_fg = "#111827"

        # 바깥 배경들 색 바꾸기
        self.root.configure(bg=bg_root)
        self.header_frame.configure(bg=bg_panel)
        self.main_frame.configure(bg=bg_panel)
        self.btn_frame.configure(bg=bg_panel)
        self.canvas.configure(bg=bg_panel)
        self.cards_frame.configure(bg=bg_panel)

        # 필터 영역/라벨/입력창 색
        self.filter_frame.configure(bg=bg_panel)
        self.search_label.configure(bg=bg_panel, fg=fg_sub)
        self.tag_label.configure(bg=bg_panel, fg=fg_sub)
        self.search_entry.configure(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)

        # 타이틀/서브타이틀 색
        self.title_label.configure(bg=bg_panel, fg=fg_title)
        self.subtitle_label.configure(bg=bg_panel, fg=fg_sub)

        # 카드 다시 그려서 색 반영
        self.apply_filters()

    def _card_bg(self):
        return "#111827" if self.theme.get() == "dark" else "#ffffff"

    def _fg(self):
        return "#e5e7eb" if self.theme.get() == "dark" else "#111827"


root = tk.Tk()
app = App(root)
root.mainloop()