# 📦 Инструкция по сборке релизов SIRSTAT

**Версия**: 1.0  
**Дата обновления**: 22 октября 2026 г.

---

## 🚀 Быстрый старт: выпуск новой версии

### Через GitHub Actions (рекомендуется)

```bash
# Переключитесь на main и обновите код
git checkout main && git pull

# Создайте тег версии (например, v1.0.0)
git tag v1.0.0

# Отправьте тег — CI автоматически соберёт приложения
git push origin v1.0.0
```

**Что произойдёт:**
1. GitHub Actions сработает на workflow **Build executable** (`.github/workflows/build.yml`)
2. Сборка параллельно для:
   - ✅ **Windows** (`SIRSTAT.exe`)
   - ✅ **macOS** (`SIRSTAT.app`)
3. По завершении job `release` автоматически создаст **GitHub Release** с артефактами

### Ручной запуск без публикации релиза

Если нужно просто проверить сборку:

```bash
# В GitHub Actions → «Build executable» → Run workflow
# Или через CLI (если настроен access)
```

CI соберёт `.exe` и `.app`, но Release не создаст.

---

## 🔨 Локальная сборка (для тестирования)

### Установка зависимостей

```bash
# Установите Python 3.10+ и зависимости
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

### Сборка через PyInstaller

```bash
# Быстрая сборка без подтверждения
pyinstaller build.spec --noconfirm

# Результат: папка dist/SIRSTAT/ с исполняемым файлом
# Для Windows: dist/SIRSTAT/SIRSTAT.exe
# Для macOS: нужно собирать на macOS (или через cross-platform)
```

### Настройка иконок

1. Положите свою иконку в корень проекта:
   - **Windows**: `app.ico` (рекомендуется 256x256)
   - **macOS**: `app.icns` (Apple recommended sizes)

2. В файле [`build.spec`](build.spec):
   ```python
   a = Analysis(
       ['1.py'],
       icon='app.ico',  # или 'app.icns' для macOS
       ...
   )
   ```

**Важно**: иконка нужна только при сборке — не обязательна в исходниках.

---

## 🔐 Подпись исполняемых файлов

### Windows: кодовая подпись (Code Signing)

См. [`SIGNING.md`](SIGNING.md) для полной инструкции по настройке:
- Получение сертификата (EV/SmartCard)
- Создание `.snk` файла
- Подписание `build.spec` через `--add-binary` или `signing` опции
- Настройка в `win_notarize` и других параметрах PyInstaller

### macOS: кодовая подпись + Notarization

1. **Подпись приложения**: используйте `codesign` после сборки:
   ```bash
   codesign --force --deep -s "СВЙ_ИМЯ_ОТДАТЕЛЯ" dist/SIRSTAT.app
   ```

2. **Notarization** (для Apple Silicon):
   ```bash
   xcrun notarytool submit dist/SIRSTAT.app \
     --keychain-profile "SIRSTAT-Apple-Profile" \
     --wait
   ```

3. **Stapling**:
   ```bash
   xcrun stapler staple dist/SIRSTAT.app
   ```

**Советы**:
- Используйте [CodeSign Pro](https://www.codesignpro.com/) или аналогичный инструмент для упрощения процесса.
- Для внутренних приложений можно использовать самоподписи (но предупреждения Gatekeeper всё равно будут).

---

## 📋 Чеклист перед выпуском релиза

- [ ] Код чист — закоммечены тесты, временные файлы
- [ ] `requirements.txt` актуален и содержит нужные версии зависимостей
- [ ] `build.spec` настроен (иконка, скрытые импорты)
- [ ] Тестовый `.exe` запускается без ошибок
- [ ] Проверена совместимость с антивирусом (не блокирует сразу)
- [ ] Логи сборки чисты (нет ошибок/предупреждений)
- [ ] `README.md` и другие файлы документации обновлены

---

## 🐛 Решение частых проблем

### Проблема: «exe не запускается / SmartScreen блокирует»

**Решение**: 
1. Подпишите исполняемый файл цифровым сертификатом (см. выше)
2. Добавьте в белый список антивируса
3. Пользователю при первом запуске: **кликните правой кнопкой → «Открыть»** (macOS аналогично — Gatekeeper)

### Проблема: «Python 3.xx не найдено»

**Решение**:
```bash
pip install -r requirements.txt --upgrade
# или переустановите Python, если версия устарела
```

### Проблема: «Матрица антибиотикограммы падает с ModuleNotFoundError: numpy.typing»

**Решение**:
Это известный случай скрытого импорта в frozen-сборках. В [`build.spec`](build.spec) уже добавлены `hiddenimports` для `numpy.typing`, но если проблема сохраняется — попробуйте:
```bash
pip install --upgrade numpy pandas
pyinstaller build.spec --noconfirm -y
```

---

## 📤 Публикация релиза вручную (если CI недоступен)

1. Соберите `.exe` и `.app` локально (см. выше)
2. Зайдите в **Releases** на GitHub
3. Нажмите «Draft a new release»
4. Заполните:
   - Tag version: `vX.Y.Z`
   - Title: `SIRSTAT vX.Y.Z Release`
   - Description: кратко опишите изменения (или ссылку на CHANGELOG)
5. Прикрепите файлы:
   - `SIRSTAT-windows.zip` (папка с `.exe`)
   - `SIRSTAT-macos.zip` (папка с `.app`)
6. Нажмите «Publish release»

---

## 📜 Лицензия и условия использования

SIRSTAT распространяется по проприетарной некоммерческой лицензии v1.0.  
Полный текст: [`LICENSE`](LICENSE)

**Кратко**:
- ✅ Бесплатно для личного/образовательного/научного использования
- ✅ Можно модифицировать под свои нужды
- ❌ Коммерческое лицензирование по запросу: **liot_public@mail.ru**

---

<div align="center">

**© 2026 Коршунов Константин Сергеевич / Kroshkos** | Все права защищены

</div>