<%*
const cats = ["To be process 개발", "Proto typing", "Sub-project", "Risk 관리"];
const cat = await tp.system.suggester(cats, cats, false, "📂 WBS 카테고리");
if (!cat) return;

const typeMap = {
  "To be process 개발": ["process 체계도", "process map", "시스템 요건 정의서", "Fit-n-Gap 해결방안 정의", "통합 테스트 시나리오"],
  "Proto typing": ["프로세스 설계", "조직구조", "데이터 정의", "Configuration", "개발항목 및 인터페이스 정의"],
  "Sub-project": ["매출마감 통합관리 체계 구축", "Special Deal and rebate 프로세스 개선", "주문 통합 시스템 구축", "고객별 출하조건 기반-재고 할당 시뮬레이션 시스템 구축", "RMA 프로세스 간소화", "PO전량 관리 프로세스 구축"],
  "Risk 관리": ["L4 기준으로 개발정의서 작성하는 불합리성 대응", "RAP modeling 역량 미확보로 인한 스펙정의서 작성 속도 지연 및 품질 저하 우려"]
};

const types = typeMap[cat];
const wbsType = await tp.system.suggester(types, types, false, "🏷️ 항목 유형");
if (!wbsType) return;

const statuses = ["todo", "in_progress", "done", "blocked"];
const status = await tp.system.suggester(statuses, statuses, false, "📌 상태");

const today = tp.date.now("YYYY-MM-DD");
_%>
---
type: wbs
wbs_category: <% cat %>
wbs_type: <% wbsType %>
registered_date: <% today %>
status: <% status || "todo" %>
start_date: 
due_date: 
end_date: 
notes: 
---

## 내용


## 기타 특이사항


## 관련 링크

