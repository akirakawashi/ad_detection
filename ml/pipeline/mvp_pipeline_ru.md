# Исправления к MVP-пайплайну анализа наружной рекламы

Текущий пайплайн хороший как база, но его нужно доработать по четырем важным направлениям:

1. Разделить detection crop и classification crop.
2. Добавить quality gate до классификатора, чтобы не классифицировать слишком дальние/мелкие объекты.
3. Добавить tracking/aggregation, чтобы понимать, что один и тот же билборд виден на разных кадрах.
4. Добавить систему score-ов: detection score, quality score, brand score, visibility score, overall score.

## 1. Важное уточнение по сущностям

В пайплайне должны быть разные уровни данных:

```text
Frame
  -> Detection
      -> Crop
          -> Classification attempt
  -> Track/Object
      -> aggregated detections
      -> best crops
      -> final brand
      -> visibility metrics
```

Одна строка `detections.csv` — это одна детекция на одном кадре.

Но для бизнесовой аналитики нужна сущность выше:

```text
track_id / object_id
```

То есть один и тот же билборд, найденный на 30 кадрах подряд, должен считаться как один объект, а не как 30 разных билбордов.

## 2. Detection и classification — разные задачи

YOLO detector отвечает только на вопрос:

```text
Где рекламная поверхность?
```

Brand classifier отвечает на вопрос:

```text
Какой бренд на crop-е?
```

Visibility module отвечает на вопрос:

```text
Насколько заметна эта реклама на маршруте?
```

Нельзя считать, что если YOLO нашла bbox, то этот bbox автоматически пригоден для классификации бренда. Если объект далеко, после crop-а бренд может быть физически нечитаемым.

## 3. Crop нужно сохранять, но не каждый crop классифицировать

Для каждой принятой детекции нужно сохранить crop в любом случае, чтобы потом можно было проверить работу пайплайна.

Но перед classifier-ом должен быть отдельный classification gate.

Пример:

```text
YOLO нашла билборд
  -> crop сохраняем всегда
  -> если crop плохой/маленький/далекий, classifier не запускаем
  -> статус = rejected_by_quality / unreadable / too_far
```

## 4. Разделить пороги detection и classification

Сейчас в черновике указано:

```text
min_crop_width: 32 px
min_crop_height: 32 px
```

Это может быть допустимо для сохранения детекции, но не для классификации бренда.

Нужно ввести два набора порогов.

### Detection gate

Используется, чтобы понять, сохраняем ли детекцию вообще.

Черновые пороги:

```text
detector_conf_min: 0.25-0.35
min_detection_width: 32 px
min_detection_height: 32 px
min_bbox_area_ratio: 0.0005-0.001
```

### Classification gate

Используется, чтобы понять, можно ли crop отправлять в classifier.

Черновые пороги:

```text
min_classify_width: 120 px
min_classify_height: 60 px
min_classify_area_ratio: 0.002-0.005
```

Если crop меньше этих значений:

```text
quality_status = rejected
quality_reason = too_small_for_classification
status = rejected_by_quality
brand = null
```

Важно: конкретные значения нужно подобрать после просмотра первых реальных crop-ов.

## 5. Quality gate должен возвращать не только status, но и quality_score

Quality gate должен возвращать:

```text
quality_status:
  passed
  borderline
  rejected

quality_reason:
  ok
  too_small
  too_far
  blurry
  too_dark
  too_bright
  low_detector_conf
  bad_aspect_ratio
  clipped_by_frame_border

quality_score:
  float 0.0-1.0
```

Пример логики:

```text
crop достаточно крупный, не смазан, нормальная яркость:
  quality_status = passed
  quality_score = 0.85-1.0

crop неидеальный, но бренд потенциально виден:
  quality_status = borderline
  quality_score = 0.45-0.75

crop слишком мелкий/смазанный:
  quality_status = rejected
  quality_score = 0.0-0.45
```

Если `quality_status = rejected`, classifier не запускаем.

Если `quality_status = borderline`, classifier можно запустить, но финальный статус почти всегда должен быть `manual_review`, кроме случаев очень высокой уверенности.

## 6. Нужно выбирать лучший crop по объекту, а не классифицировать каждый кадр одинаково

Для видео один и тот же рекламный объект может быть виден на разных кадрах:

```text
frame 100: далеко, crop маленький
frame 110: ближе, crop лучше
frame 120: лучший кадр
frame 130: объект уходит из кадра
```

Правильная логика:

```text
1. YOLO находит detections.
2. Detections объединяются в track/object.
3. По каждому track выбираются лучшие crop-ы.
4. Classifier запускается на best crops.
5. Итоговый бренд считается по нескольким лучшим crop-ам.
```

Для MVP можно начать с простой логики:

```text
для каждого track выбрать top-N crop-ов по quality_score * area_ratio * det_conf
```

Например:

```text
best_crops_per_track: 3 или 5
```

Только эти crop-ы отправлять в classifier.

## 7. Tracking / aggregation нужен для подсчета видимости

В первой версии можно реализовать простую IoU-агрегацию между соседними обработанными кадрами.

Пример:

```text
если detection на frame N и detection на frame N+stride имеют IoU >= 0.3-0.5,
считать их одним track_id
```

Поля track:

```text
track_id
source_path
first_frame_index
last_frame_index
first_timestamp_sec
last_timestamp_sec
detections_count
best_crop_path
best_quality_score
max_area_ratio
mean_area_ratio
mean_visibility_score
final_brand
final_brand_conf
final_status
```

Важно: для MVP `track_id` означает “один объект внутри одного видео/прохода”. Это не глобальный ID билборда в реальном мире. Чтобы понимать, что это тот же самый физический билборд в разные дни/маршруты, позже понадобятся GPS, геопривязка, re-identification или ручная связка.

## 8. Как считать видимость

Нужно не просто определить бренд, но и посчитать, насколько объект был заметен.

Для каждой detection считаем:

```text
area_ratio = bbox_area / frame_area
center_x_norm = bbox_center_x / frame_width
center_y_norm = bbox_center_y / frame_height
position_label = left/top, right-middle и т.д.
```

Дополнительно нужно посчитать `position_weight`.

Пример простой логики:

```text
объект ближе к центру кадра -> position_weight выше
объект на краю кадра -> position_weight ниже
```

Черновая логика:

```text
center_distance = distance from frame center, normalized 0..1
position_weight = 1.0 - center_distance
position_weight clipped to 0.2..1.0
```

Потом считаем frame-level visibility:

```text
visibility_score = area_score * position_weight * quality_score
```

Где:

```text
area_score = normalized area_ratio
quality_score = из quality gate
```

Для MVP можно упростить:

```text
visibility_score = area_ratio * position_weight * quality_score
```

По track считаем:

```text
track_visibility_score = sum или mean visibility_score по detections track-а
track_visible_duration_sec = last_timestamp_sec - first_timestamp_sec
track_max_area_ratio = max(area_ratio)
track_mean_area_ratio = mean(area_ratio)
```

Для отчета полезно иметь две метрики:

```text
object_count_visibility:
  сколько уникальных рекламных объектов найдено по брендам

exposure_visibility:
  сколько времени/кадров бренд был виден и с какой площадью
```

## 9. Добавить overall score

Нужно считать не один score, а несколько:

```text
det_score        — уверенность YOLO detector
quality_score    — насколько crop пригоден для анализа
brand_score      — уверенность classifier
visibility_score — насколько объект заметен в кадре
overall_score    — общий score для карточки/отчета
```

### Per-detection overall_score

Для одной детекции:

```text
overall_score = 
  0.30 * det_conf +
  0.30 * quality_score +
  0.25 * brand_conf +
  0.15 * visibility_score_norm
```

Если classifier не запускался:

```text
brand_conf = 0
overall_score = 
  0.40 * det_conf +
  0.40 * quality_score +
  0.20 * visibility_score_norm
```

### Per-track final_score

Для объекта/track:

```text
track_final_score =
  0.30 * mean_det_conf +
  0.25 * best_quality_score +
  0.25 * final_brand_conf +
  0.20 * track_visibility_score_norm
```

Значения весов на MVP можно оставить конфигурируемыми.

## 10. Финальный бренд нужно считать по track, а не только по одной detection

Если classifier запускается на нескольких best crop-ах одного track-а, нужно агрегировать предсказания.

Пример:

```text
crop_1: mts 0.82
crop_2: mts 0.76
crop_3: miranda 0.51
```

Итог:

```text
final_brand = mts
final_brand_conf = средняя/максимальная уверенность по mts
final_status = detected_brand или manual_review
```

Если предсказания конфликтуют:

```text
crop_1: mts 0.72
crop_2: miranda 0.70
crop_3: plus7 0.66
```

Итог:

```text
final_status = manual_review
final_brand = null или наиболее вероятный бренд с пометкой conflict
quality_reason/status_reason = brand_conflict_across_track
```

## 11. Обновить статусы

Текущие статусы нормальные, но их нужно расширить.

```text
status:
  detected_brand
  other
  unknown
  manual_review
  rejected_by_quality
  too_far
  unreadable
```

Можно оставить `rejected_by_quality` как общий статус, а причину хранить отдельно:

```text
quality_reason:
  too_small
  too_far
  blurry
  too_dark
  too_bright
```

Для бизнес-отчета важно разделять:

```text
unknown — модель не уверена
unreadable/too_far — по изображению физически нельзя понять бренд
manual_review — можно проверить человеком
other — реклама не из целевых телеком-брендов
```

## 12. Обновить detections.csv

Добавить поля:

```text
run_id
source_path
input_type
frame_index
timestamp_sec
det_index
track_id

det_class
det_conf

bbox_x1
bbox_y1
bbox_x2
bbox_y2
bbox_width
bbox_height
bbox_area
area_ratio

center_x
center_y
center_x_norm
center_y_norm
position_label
position_weight

crop_path
crop_width
crop_height

quality_status
quality_reason
quality_score

classification_attempted
brand_pred
brand_conf
top1_brand
top1_score
top2_brand
top2_score
top3_brand
top3_score

visibility_score
overall_score

status
status_reason
```

## 13. Добавить tracks.csv

Нужна отдельная таблица по уникальным объектам.

```text
tracks.csv
```

Колонки:

```text
run_id
source_path
track_id

first_frame_index
last_frame_index
first_timestamp_sec
last_timestamp_sec
visible_duration_sec

detections_count
classified_crops_count

best_crop_path
best_frame_index
best_timestamp_sec

mean_det_conf
max_det_conf

mean_quality_score
best_quality_score

max_area_ratio
mean_area_ratio
sum_area_ratio

mean_position_weight
mean_visibility_score
sum_visibility_score

final_brand
final_brand_conf
final_status
final_status_reason

track_final_score
manual_review_required
```

Именно `tracks.csv` должен использоваться для подсчета количества уникальных рекламных объектов.

`detections.csv` нужен для отладки покадровой работы.

## 14. Обновить brand_summary.csv

Агрегацию по брендам лучше строить не только по detections, но и по tracks.

Добавить две версии:

```text
brand_summary_by_detections.csv
brand_summary_by_tracks.csv
```

В `brand_summary_by_tracks.csv`:

```text
brand
status
track_count
mean_track_final_score
mean_visibility_score
sum_visibility_score
mean_final_brand_conf
max_final_brand_conf
first_timestamp_sec
last_timestamp_sec
```

## 15. Обновить графики

Нужны не только графики по брендам, но и графики по visibility/score.

Минимальный набор:

```text
charts/
  detections_by_brand.png
  tracks_by_brand.png
  status_counts.png
  confidence_distribution.png
  quality_score_distribution.png
  visibility_by_brand.png
  visibility_timeline.png
  area_ratio_timeline.png
  manual_review_cases.png
```

### visibility_timeline

По X:

```text
timestamp_sec
```

По Y:

```text
sum visibility_score по кадру
```

Группировка:

```text
brand/status
```

### visibility_by_brand

По брендам:

```text
sum_visibility_score
mean_visibility_score
track_count
```

## 16. Обновить визуализацию на видео

На annotated video рядом с bbox нужно показывать карточку:

```text
Brand: MTS
Status: detected_brand
Det: 0.87
Cls: 0.82
Q: 0.74
Area: 2.1%
Vis: 0.63
Score: 0.79
Track: 12
```

Если crop не классифицировался:

```text
Status: too_far
Reason: too_small_for_classification
Det: 0.71
Q: 0.22
Area: 0.1%
Track: 8
```

Важно: если объект `manual_review`, `unknown` или `too_far`, нельзя рисовать карточку так, будто бренд подтвержден.

## 17. Обновить HTML report

В отчете нужно разделить:

### 1. Detection summary

```text
сколько рекламных поверхностей найдено покадрово
```

### 2. Track/object summary

```text
сколько уникальных рекламных объектов найдено
```

### 3. Brand summary

```text
сколько объектов каждого бренда
```

### 4. Visibility summary

```text
видимость по брендам:
- track_count
- sum_visibility_score
- mean_visibility_score
- max_area_ratio
- visible_duration_sec
```

### 5. Quality summary

```text
сколько объектов не удалось классифицировать из-за:
- too_small
- too_far
- blur
- low_confidence
```

### 6. Manual review gallery

```text
crop-ы, которые нужно проверить руками
```

### 7. Best detections gallery

```text
лучшие crop-ы по track_final_score
```

## 18. Обновить порядок реализации

Правильный порядок реализации MVP:

```text
1. Image pipeline:
   image -> detector -> crops -> detections.csv -> annotated image

2. Video sampling:
   video -> sampled frames -> detector -> detections.csv -> crops

3. Quality gate:
   quality_status, quality_reason, quality_score

4. Classification:
   запускать classifier только для passed/borderline crop-ов

5. Scoring:
   det_score, quality_score, brand_score, visibility_score, overall_score

6. Simple tracking:
   detections -> track_id через IoU на соседних кадрах

7. Track aggregation:
   best crops, final_brand, final_status, track_final_score

8. Reports:
   detections.csv, tracks.csv, summaries

9. Visualization:
   annotated frames/video с карточками

10. Charts + HTML report
```

## 19. Конфиг MVP

Добавить конфиг:

```text
frame_stride: 5

detector_conf_min: 0.30
min_detection_width: 32
min_detection_height: 32
min_detection_area_ratio: 0.0005

min_classify_width: 120
min_classify_height: 60
min_classify_area_ratio: 0.002

crop_margin_ratio: 0.05

quality_pass_min: 0.65
quality_borderline_min: 0.40

brand_conf_accept: 0.80
other_conf_accept: 0.85
manual_review_min: 0.50

tracking_iou_min: 0.35
max_track_gap_frames: 2
best_crops_per_track: 3
```

Все значения должны быть вынесены в config и легко меняться.

## 20. Главное изменение в понимании результата

Для бизнес-метрик использовать не `detections.csv`, а `tracks.csv`.

`detections.csv` отвечает на вопрос:

```text
Что модель увидела на каждом кадре?
```

`tracks.csv` отвечает на вопрос:

```text
Какие уникальные рекламные объекты были на маршруте?
```

`brand_summary_by_tracks.csv` отвечает на вопрос:

```text
Сколько уникальных объектов каждого бренда было найдено?
```

`visibility_by_brand` отвечает на вопрос:

```text
Насколько заметен каждый бренд на маршруте?
```

Это ключевая поправка к пайплайну.
