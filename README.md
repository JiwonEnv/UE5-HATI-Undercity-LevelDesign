# HATI : Undercity

> 남겨진 자들의 기록 — 셸터 도시 **하층** 레벨디자인 포트폴리오 (Unreal Engine 5.8)

컨셉 기획서 『HATI – 남겨진 자들의 기록』을 바탕으로 만드는 스토리 중심 3인칭 액션 어드벤처의 레벨디자인 프로젝트입니다.
무대는 23세기 거대 셸터 도시의 최하층(지면 접촉 구역)이고, 3개의 씬으로 나눠 블록아웃 → 플레이테스트 → 아트 패스 순서로 진행합니다.

## 열기
`HATI_Undercity.uproject`를 더블클릭하세요(UE 5.8). 에디터는 `L_Dev_Sandbox`에서 시작합니다.

## 폴더 구조
```
Content/
  HATI/
    Maps/Dev/        L_Dev_ScaleGym (치수 테스트), L_Dev_Sandbox (자유 블록아웃)
    Maps/Scenes/     씬별 레벨 (정해지는 대로 추가)
    Blockout/        Materials (MI_BO_*), Meshes, Prefabs
    Blueprints/ Characters/ Environment/ Props/ Materials/ Textures/ VFX/ Audio/ UI/ Cinematics/ Data/
  LevelPrototyping/  엔진 기본 블록아웃 메쉬·그리드 머티리얼 (SM_Cube, SM_Ramp, M_PrototypeGrid ...)
  ThirdPerson/ Characters/ Input/   3인칭 템플릿 (플레이어 캐릭터, 입력)
Tools/setup_blockout.py             위 HATI 블록아웃 에셋을 다시 만드는 스크립트
```

## 블록아웃 색상 규칙 (`/Game/HATI/Blockout/Materials`)
모든 머티리얼은 **월드 좌표 기준 그리드**라서 큰 칸 1개가 1m, 작은 칸 1개가 25cm입니다. 오브젝트를 늘려도 격자가 늘어나지 않습니다.

| 머티리얼 | 색 | 의미 |
|---|---|---|
| MI_BO_Floor | 회색 | 걸을 수 있는 바닥 |
| MI_BO_Wall | 짙은 남색 | 벽·경계(통과 불가) |
| MI_BO_Path | 밝은 회백색 | 주 동선·유도 경로 |
| MI_BO_Cover | 주황 갈색 | 전투 엄폐물 |
| MI_BO_Traversal | 노랑 | 오르기·점프 구간 |
| MI_BO_Hazard | 빨강 | 오염·위험 지역 |
| MI_BO_Interact | 청록 | 목표·상호작용·NPC 위치 |
| MI_BO_Restricted | 보라 | 상층·차단벽 등 접근 불가 |
| MI_BO_Toxic | 독성 초록 | 오염된 액체·환기구 |
| MI_BO_Prop | 갈색 | 잡동사니·폐기물 |

## 스케일 기준 (L_Dev_ScaleGym)
UE 기본 마네킹 기준(키 약 180cm, 캡슐 반경 42cm)이며, 짐 맵에서 직접 걸어보면서 확인합니다.
- 벽·엄폐 높이: 50 / 100(낮은 엄폐) / 150(높은 엄폐) / 200 / 300 / 400
- 점프로 오를 수 있는 높이: 25 ~ 150
- 점프 간격: 150 ~ 500
- 경사: 15 / 30 / 45 / 50° (걸을 수 있는 한계 약 44°)
- 계단 높이: 15 / 20 / 30 / 45 / 50 (오를 수 있는 한계 약 45)
- 복도 폭: 100 ~ 400, 문 크기 100×220

## 커밋 규칙
[Docs/COMMIT_CONVENTION.md](Docs/COMMIT_CONVENTION.md) — `<타입>(<스코프>): <제목>` 형식이고, 설명은 모두 한글로 씁니다. 제목만 읽어도 무엇을 했는지 알 수 있게 씁니다.
템플릿 등록: `git config commit.template .gitmessage`

## 작업 팁
- `Shift+5` → Modeling Mode (CubeGrid, PolyEdit, Boolean)로 형태를 빠르게 잡습니다.
- 뷰포트 스냅은 위치 50/100, 회전 15°를 권장합니다.
- 블록아웃 단계에서는 동선·시야·높낮이만 봅니다. 디테일은 플레이테스트 이후에 올립니다.
