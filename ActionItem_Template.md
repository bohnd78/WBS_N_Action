<%*
const actionTypes = [
  "task list 및 관련 일정표 작성",
  "미팅(출장)",
  "문서작성",
  "개발(분석/설계)",
  "준비작업",
  "역량확보",
  "테스트"
];
const actionType = await tp.system.suggester(actionTypes, actionTypes, false, "🏷️ Action 유형");
if (!actionType) return;

const statuses = ["todo", "in_progress", "done", "blocked"];
const status = await tp.system.suggester(statuses, statuses, false, "📌 상태");

const today = tp.date.now("YYYY-MM-DD");
_%>
---
type: action_item
action_type: <% actionType %>
registered_date: <% today %>
status: <% status || "todo" %>
start_date: 
due_date: 
end_date: 
wbs_ref: 
notes: 
---

## 내용


## 기타


## 체크리스트
- [ ] 
- [ ] 
- [ ] 

