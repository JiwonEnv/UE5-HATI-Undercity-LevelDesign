# HATI : Undercity

> 남겨진 자들의 기록 — 셸터 도시 **하층** 레벨디자인 포트폴리오 (Unreal Engine 5.8)

컨셉 기획서 『HATI – 남겨진 자들의 기록』을 바탕으로 만드는 스토리 중심 3인칭 액션 어드벤처의 레벨디자인 프로젝트입니다.
무대는 23세기 거대 셸터 도시의 최하층(지면 접촉 구역)이고, 3개의 씬으로 나눠 블록아웃 → 플레이테스트 → 아트 패스 순서로 진행합니다.

## 열기
`HATI_Undercity.uproject`를 더블클릭하세요(UE 5.8). 에디터는 `L_Dev_Sandbox`에서 시작합니다.

## 폴더 구조
**원칙: 우리가 만드는 것은 전부 `HATI/` 안에, 템플릿에서 온 것은 `_Template/` 안에 둡니다.**

```
Content/
├─ HATI/                  ← 우리 작업물
│  ├─ Maps/
│  │  ├─ Scenes/          씬 1~3 실제 레벨 (정해지는 대로 추가)
│  │  └─ Dev/             테스트 맵: L_Dev_ScaleGym (치수), L_Dev_Sandbox (자유 블록아웃),
│  │                      L_Dev_PCGBiome (실내 PCG), L_Dev_PCGBiome_Outdoor (쉘터 바깥 PCG)
│  ├─ Blockout/           Materials (MI_BO_*), Meshes, Prefabs
│  ├─ Environment/        배경 메시·머티리얼·텍스처 (구역별 하위 폴더)
│  ├─ Props/              소품
│  ├─ PCG/                PCG 그래프, HATI용 Biome Definition·Asset
│  └─ Blueprints/ Characters/ VFX/ Audio/ UI/ Cinematics/ Data/
└─ _Template/             UE 템플릿에서 온 것 (직접 수정하지 않음)
   ├─ LevelPrototyping/   기본 블록아웃 메시·그리드 머티리얼 (SM_Cube, SM_Ramp, M_PrototypeGrid …)
   ├─ ThirdPerson/        3인칭 캐릭터·게임모드 BP, 예제 맵 Lvl_ThirdPerson
   ├─ Characters/         마네킹 (Manny, Quinn)
   └─ Input/              입력 액션·매핑
Tools/setup_blockout.py             HATI 블록아웃 에셋을 다시 만드는 스크립트
Tools/setup_pcg_biome_test.py       PCG Biome 테스트 맵(L_Dev_PCGBiome)을 다시 만드는 스크립트
Tools/setup_pcg_biome_outdoor.py    PCG Biome 실외 테스트 맵을 다시 만드는 스크립트
Tools/reorganize_content.py         템플릿 폴더를 _Template으로 옮긴 1회용 스크립트 (기록용)
```

- 빈 폴더는 Git에 올라가지 않아서 `.gitkeep` 파일을 넣어 두었습니다. 에디터에는 보이지 않는 파일이니 무시하면 됩니다.
- Content Browser 설정(오른쪽 위 Settings)에서 **Show Engine Content는 끄고**, Biome 샘플을 볼 때만 **Show Plugin Content**를 켭니다.
- 에셋을 옮기거나 이름을 바꿀 때 "Not checked-out or writable" 오류가 나면 파일이 읽기 전용인 것입니다. `.gitattributes`의 LFS `lockable` 설정 때문이며, 파일 속성에서 읽기 전용을 풀면 됩니다.

## PCG Biome Core 테스트 (2026-11-25 ~, Experimental)
Epic의 **PCG Biome Core**를 "환경 구역 클러터" 도구로 쓸 수 있는지 시험합니다. 여기서 바이옴은 자연 지형이 아니라 오염 구역, 폐기물 적치장, 거주 구역 같은 구역 단위입니다.
- 플러그인: `PCG`, `PCGGeometryScriptInterop`, `PCGBiomeCore`, `PCGBiomeSample` (엔진 Experimental 플러그인)
- 테스트 맵: `Maps/Dev/L_Dev_PCGBiome` — 40×40m 메시 바닥 방
  - 북동쪽 빨간 바닥 = `PCG_Biome_Contamination` (Biome Volume, 임시로 Sample의 *Landslide* 바위 사용)
  - 가운데 주 동선 = `PCG_Exclusion_Path` (Exclusion Volume, 동선과 엄폐물을 비워 둠)
  - 남서쪽 = 비교용 빈 구역
- 다시 만들기: `UnrealEditor.exe HATI_Undercity.uproject -ExecutePythonScript="Tools/setup_pcg_biome_test.py" -HATIQuit`
- 원칙: 플레이테스트가 끝날 때까지 `Maps/Scenes` 씬 레벨에는 넣지 않습니다. 실제로 쓰게 되면 공식 권장대로 플러그인을 프로젝트 `Plugins/`에 복사해서 씁니다.
- **1차 결과 (2026-11-25): 메시 바닥에서는 아무것도 생성되지 않음 (0개).** Biome Volume에 Definition과 Assets(Landslide)를 넣었지만, Sample의 제너레이터(`BiomesGenerator_SG_Sampler_*`)와 기본 템플릿(`TPL_BiomeCore_Generator`)이 **Get Landscape Data**로 점을 뽑기 때문에 랜드스케이프가 없으면 점이 생기지 않습니다. 어셈블리 배치용 표면 입력(`WorldRayHitSetting`)은 스태틱 메시도 지원합니다.
- **실외 테스트 (2026-11-25): 성공, 약 16,700개 생성.** `Maps/Dev/L_Dev_PCGBiome_Outdoor` — 쉘터 바깥을 가정한 맵입니다. Python으로는 랜드스케이프를 만들 수 없어서 Biome Sample 맵의 1km 지형을 복사했고, Epic의 바이옴 배치는 지운 뒤 우리 구역을 다시 깔았습니다. 다시 만들기: `Tools/setup_pcg_biome_outdoor.py`
  - `Wasteland`(Desert): 드문드문한 선인장과 관목 / `DeadForest`(ConiferousForest): 빽빽한 침엽수 / `RubbleField`(Landslide): 바위(구역 대부분이 호수라 적게 생성됨)
  - `Exclusion_Road`(제외 스플라인): 쉘터 게이트로 가는 길 / `Exclusion_Gate`(제외 볼륨) + 보라색 쉘터 외벽 블록아웃
  - 확인용 스크린샷: `Saved/Screenshots/WindowsEditor/PCGBiome_Outdoor.png`
- 실내(메시 바닥) 다음 할 일: ① Sampler 그래프를 프로젝트로 복사해 Get Landscape Data를 메시 표면 샘플링으로 바꾸기, 또는 ② 테스트용 평평한 랜드스케이프를 깔아 원래 흐름부터 확인하기 → 그다음 자체 폐기물 에셋으로 Biome Definition/Asset 만들기, 부모-자식 배치(컨테이너 주변 잔해)

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

## 조명·노출 규칙
범위는 프로젝트 설정으로 넉넉히 잡고, 각 맵의 분위기는 조명과 Post Process Volume으로 맞춥니다.

1. **프로젝트 전체** (`Config/DefaultEngine.ini`): `r.EyeAdaptation.CachedLightingPreExposure=6`
   - Lumen과 스카이 캡처가 깨끗하게 저장하는 노출 범위를 EV -8~12(기본)에서 **-6~14**로 넓힙니다.
   - 어두운 지하와 맑은 실외를 둘 다 담기 위한 값입니다. 화면에 "Cached lighting in Lumen … is going to be clipped" 경고가 뜨면 이 범위를 벗어난 것입니다.
2. **맵마다**: 맵 전체에 적용되는(Infinite Extent) Post Process Volume `PPV_Global`을 하나 두고 노출 범위를 정합니다.
   | 분위기 | Min / Max EV100 | 예 |
   |---|---|---|
   | 맑은 실외 | 10 / 14 | `L_Dev_PCGBiome_Outdoor` |
   | 어두운 지하 | -2 / 6 (조명 작업 때 조정) | 씬 레벨 |
   - `Tools/setup_post_process.py`의 `PRESETS`에 맵을 추가하고 실행하면 `PPV_Global`이 들어갑니다.

## 커밋 규칙
[Docs/COMMIT_CONVENTION.md](Docs/COMMIT_CONVENTION.md) — `<타입>(<스코프>): <제목>` 형식이고, 설명은 모두 한글로 씁니다. 제목만 읽어도 무엇을 했는지 알 수 있게 씁니다.
템플릿 등록: `git config commit.template .gitmessage`

## 작업 팁
- `Shift+5` → Modeling Mode (CubeGrid, PolyEdit, Boolean)로 형태를 빠르게 잡습니다.
- 뷰포트 스냅은 위치 50/100, 회전 15°를 권장합니다.
- 블록아웃 단계에서는 동선·시야·높낮이만 봅니다. 디테일은 플레이테스트 이후에 올립니다.
