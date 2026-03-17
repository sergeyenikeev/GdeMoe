# Datasets: download & layout (Windows / PowerShell)

## Why Kaggle
Некоторые источники (Open Images v7/v6 official buckets, отдельные академические хостинги) могут быть requester-pays/падать/менять URL.
Kaggle часто остаётся самым стабильным способом скачать датасеты (но нужно принять условия/лицензию на странице датасета).

## Prerequisites
1) Установлен Python и `kaggle`:
```powershell
python -m pip install --user kaggle
```

2) Токен Kaggle лежит в `C:\Users\<you>\.kaggle\kaggle.json`:
```powershell
$env:KAGGLE_CONFIG_DIR="$env:USERPROFILE\.kaggle"
New-Item -ItemType Directory -Force -Path $env:KAGGLE_CONFIG_DIR | Out-Null
Move-Item -Path "C:\Users\<you>\Downloads\kaggle.json" -Destination "$env:KAGGLE_CONFIG_DIR\kaggle.json"
```

3) Добавить `kaggle.exe` в PATH (для текущей сессии PowerShell):
```powershell
$env:Path = "$env:USERPROFILE\AppData\Roaming\Python\Python311\Scripts;$env:Path"
```

Проверка:
```powershell
kaggle --version
```

Если при скачивании получаете `403`, откройте страницу датасета в браузере и нажмите “Download/Accept” (принять условия).

## Folder layout
Рекомендуемый корень: `D:/datasets/`
- `D:/datasets/coco/`
- `D:/datasets/open_images/`
- `D:/datasets/rpc/`
- `D:/datasets/sku110k/`
- `D:/datasets/grozi/`

## COCO 2017 (official, public)
Скачивание (пример):
```powershell
$dst="D:/datasets/coco"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Invoke-WebRequest "http://images.cocodataset.org/zips/train2017.zip" -OutFile "$dst/train2017.zip"
Invoke-WebRequest "http://images.cocodataset.org/zips/val2017.zip" -OutFile "$dst/val2017.zip"
Invoke-WebRequest "http://images.cocodataset.org/annotations/annotations_trainval2017.zip" -OutFile "$dst/annotations_trainval2017.zip"
Expand-Archive "$dst/train2017.zip" -DestinationPath $dst
Expand-Archive "$dst/val2017.zip" -DestinationPath $dst
Expand-Archive "$dst/annotations_trainval2017.zip" -DestinationPath $dst
```

## Open Images annotations (без GCP billing)
Вариант: взять CSV-аннотации через Kaggle (официальные buckets могут требовать billing).

Рекомендуемый датасет (аннотации/списки, **без** 9M изображений):
- `programmerrdai/open-images-v6`

Скачать только нужные файлы в `D:/datasets/open_images/annotations`:
```powershell
$dst="D:/datasets/open_images/annotations"
New-Item -ItemType Directory -Force -Path $dst | Out-Null

kaggle datasets download -d programmerrdai/open-images-v6 -f "validation-annotations-bbox.csv" -p $dst --unzip
kaggle datasets download -d programmerrdai/open-images-v6 -f "test-annotations-bbox.csv" -p $dst --unzip
kaggle datasets download -d programmerrdai/open-images-v6 -f "oidv6-train-annotations-bbox/oidv6-train-annotations-bbox.csv" -p $dst --unzip
kaggle datasets download -d programmerrdai/open-images-v6 -f "train-images-boxable-with-rotation/train-images-boxable-with-rotation.csv" -p $dst --unzip
kaggle datasets download -d programmerrdai/open-images-v6 -f "oidv6-class-descriptions (1).csv" -p $dst --unzip
```

Дальше можно использовать `scripts/dataset_subset.py --dataset openimages ...` (передав пути к этим CSV).

## RPC (Retail Product Checkout) (research, CC-BY-NC-SA)
Официальные прямые URL могут меняться; стабильнее через Kaggle:
- `diyer22/retail-product-checkout-dataset` (~27GB)

```powershell
$dst="D:/datasets/rpc"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
kaggle datasets download -d diyer22/retail-product-checkout-dataset -p $dst --unzip
```

## SKU-110K (research, CC BY-NC-SA)
Kaggle зеркало с картинками + аннотациями:
- `thedatasith/sku110k-annotations` (~14GB)

```powershell
$dst="D:/datasets/sku110k"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
kaggle datasets download -d thedatasith/sku110k-annotations -p $dst --unzip
```

## GroZi (grocery, small)
Пример YOLO-формата на Kaggle:
- `saiakash/grozi-yolo`

```powershell
$dst="D:/datasets/grozi"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
kaggle datasets download -d saiakash/grozi-yolo -p $dst --unzip
```

## Helpful commands
Показать список файлов внутри датасета:
```powershell
kaggle datasets files -d diyer22/retail-product-checkout-dataset --page-size 200
```
