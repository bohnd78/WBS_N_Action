# Project Agent - ERP 컨설턴트 WBS & Action Item 관리

## 📱 Obsidian iPhone 플러그인 설치 가이드

### 1단계: Community Plugins 활성화
1. Obsidian 앱 실행 → 우측 하단 **⚙️ Settings**
2. **Community Plugins** 탭 → **"Turn on community plugins"** 버튼 탭
3. **"I understand..."** 확인

### 2단계: Templater 플러그인 설치 (핵심)
1. Community Plugins → **Browse** 탭
2. 검색창에 **"Templater"** 입력
3. **Templater by SilentVoid13** → **Install** → **Enable**
4. Settings → Community Plugins → Templater ⚙️
   - **Template folder location**: `Templates` 입력 (볼트 내 폴더명)
   - **Trigger Templater on new file creation**: ON
   - **Enable Folder Templates**: ON (선택사항)

### 3단계: Tasks 플러그인 설치
1. Browse → **"Tasks"** 검색
2. **Tasks by Martin Schenk** → Install → Enable
3. Settings → Tasks:
   - **Global task filter**: `#action` (선택사항)
   - **Set done date on every completed task**: ON

### 4단계: Dataview 플러그인 설치
1. Browse → **"Dataview"** 검색
2. **Dataview by Michael Brenan** → Install → Enable
3. Settings → Dataview:
   - **Enable JavaScript Queries**: ON
   - **Inline Query Prefix**: `=`

### 5단계: 템플릿 파일 복사
`obsidian_templates/` 폴더의 두 파일을 Obsidian Vault의 `Templates/` 폴더에 복사:
- `WBS_Template.md`
- `ActionItem_Template.md`

### 6단계: 모바일에서 템플릿 사용법
1. 새 노트 생성 (우측 상단 **✏️** 아이콘)
2. 우측 하단 **명령어 팔레트** (리본 바) 탭
3. **"Templater: Open Insert Template Modal"** 선택
4. `WBS_Template` 또는 `ActionItem_Template` 선택
5. 팝업 선택 화면에서 카테고리 → 항목 유형 → 상태 순으로 선택
6. 자동 생성된 Frontmatter 확인 후 내용 작성

---

## 🚀 웹 애플리케이션 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 앱 실행 (원격 접근 허용)
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# 3. 모바일에서 접속
# http://<서버IP>:8501
```

### 방화벽 설정 (필요시)
```bash
# Ubuntu/Debian
sudo ufw allow 8501

# macOS (원격 Mac 기준)
# 시스템 설정 → 방화벽 → 포트 8501 허용
```

---

## 📂 프로젝트 파일 구조

```
project_agent/
├── app.py                    # Streamlit 메인 앱
├── database.py               # SQLite CRUD + 마스터 데이터
├── parser.py                 # Obsidian 마크다운 파서
├── requirements.txt          # 의존성
├── project_agent.db          # SQLite DB (앱 실행 후 자동 생성)
└── obsidian_templates/
    ├── WBS_Template.md       # Obsidian WBS 입력 템플릿
    └── ActionItem_Template.md # Obsidian Action Item 템플릿
```

---

## 🔄 워크플로우

```
[현장] iPhone Obsidian
  → WBS_Template / ActionItem_Template으로 노트 작성
  → iCloud/Obsidian Sync로 동기화

[원격 서버] Streamlit App
  → 📤 노트 업로드 탭에서 .md 파일 업로드
  → 자동 파싱 → WBS / Action Item으로 분류 저장
  → 📋 WBS 관리 / ✅ Action Items에서 관리
  → ⚙️ 시스템/데이터 관리에서 항목 유형 추가/삭제
```

---

## 🛣️ 향후 개발 로드맵

- **Phase 3**: Gantt 차트 / 캘린더 뷰 추가
- **Phase 4**: LLM Agent (노트 → Action Item 자동 추출, 진행 전략 제안)
- **Phase 5**: Knowledge Graph (Neo4j / NetworkX) 연동
- **Phase 6**: SAP IMG 설정 지식 + RAP 프로그래밍 RAG Q&A
- **Phase 7**: ABAP 분석 에이전트 채팅 서비스
