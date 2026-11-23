# 🔐 Подпись сборок SIRSTAT (Code Signing)

**Цель**: убрать предупреждения Windows SmartScreen/macOS Gatekeeper о "неизвестном издателе" и повысить доверие пользователей к приложениям.

---

## 📌 Обзор

Workflow `.github/workflows/build.yml` автоматически подписывает исполняемые файлы при наличии секретов в репозитории:
- **Windows**: Authenticode подпись (EV/OV сертификаты)
- **macOS**: Developer ID + notarization (Apple Notarization)

**Без секретов**: сборки выходят неподписанными, но запускаются без проблем (возможно, потребуется разрешить от SmartScreen/Gatekeeper).

---

## 🪟 Windows — Authenticode (EV или OV сертификат)

### Что понадобится

1. **Сертификат Code Signing** от аккредитованного CA:
   - DigiCert / Sectigo / GlobalSign / SSL.com
   - Рекомендуется **EV (Extended Validation)** для максимального доверия SmartScreen
   - Некоторые CA выдают его в облачном HSM (подпись через их CLI/REST API)

2. **PFX-файл** с сертификатом и приватным ключом
3. **Пароль** от PFX-файла

### Настройка в GitHub

```bash
# В Settings → Secrets and variables → Actions → New repository secret
WIN_CODESIGN_P12_BASE64  # base64(PFX-файл), например: [Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.p12"))
WIN_CODESIGN_PASSWORD     # пароль от PFX

# Для macOS (опционально):
MAC_INSTALLER_CERT_BASE64  # base64(Developer ID .p12)
MAC_INSTALLER_CERT_PASSWORD # пароль
MAC_KEYCHAIN_PASSWORD      # временный пароль для keychain на раннере
APPLE_ID                   # email аккаунта Apple Developer
APPLE_APP_PASSWORD         # app-specific password (appleid.apple.com → Sign-In and Security)
APPLE_TEAM_ID              # Team ID (Account → Membership)
```

### Как workflow подписывает сборку

1. Импортирует сертификат во временное хранилище раннера
2. Подписывает:
   - `dist/SIRSTAT.exe`
   - Все DLL в `dist/SIRSTAT/`
3. Использует **SHA-256 + timestamp** для максимальной длительности валидности

---

## 🍎 macOS — Developer ID + Notarization

### Что понадобится

1. **Аккаунт Apple Developer Program** ($99/год)
2. **Сертификат Developer ID Application**, экспортированный в `.p12` вместе с приватным ключом
3. Настройка hardened runtime через `macos-entitlements.plist`:
   - `NSOpenPanel` (чтение выбранных файлов пользователем)
   - `disable-library-validation` (для PyInstaller, где динамические `.so` подписаны нашим же сертификатом)

### Процесс notarization

Workflow:
1. Импортирует `.p12` во временный keychain
2. Подписывает `.app` с hardened runtime и entitlements
3. Отправляет на нотаризацию через `notarytool submit --wait`
4. Stapling через `stapler staple`

**Результат**: Gatekeeper принимает приложение без предупреждений при установке.

---

## 💰 Бесплатная альтернатива для macOS

Если нет Apple Developer Account:

1. Оставьте **adhoc подпись** (не подписанный сертификат)
2. В тексте релиза укажите:
   ```markdown
   ⚠️ Приложение самоподписано. При первом запуске может появиться предупреждение от Gatekeeper:
   
   1. Кликните правой кнопкой на `SIRSTAT.app` → Открыть (это разрешит Gatekeeper)
   2. Или снимите quarantine вручную: xattr -dr com.apple.quarantine /путь/к/SIRSTAT.app
   
   Если вы не являетесь пользователем macOS, обратитесь к IT-отделу для настройки исключений в антивирусе.
   ```

---

## 🛡️ Что ещё снижает «ругань» антивирусов

- **Подпись** — основной фактор доверия
- **one-dir** вместо one-file:
  - One-file распаковывает 150–300 МБ каждый запуск → антивирус проверяет каждый файл → медленно
  - One-dir запускается сразу, без распаковки
- **Минимальный набор библиотек** в `build.spec` (excludes):
  - Исключены: PIL, sqlite3, unittest, setuptools, pip, тесты pandas/numpy
  - Меньше размер → быстрее импорт → меньше триггерей heuristics

---

## 🚀 Оптимизация производительности сборки и запуска

### one-dir vs one-dir

```python
# В build.spec:
a = Analysis(
    ...
    noarchive=False,  # by default (one-dir)
    ...
)
```

**Плюсы one-dir**:
- Быстрый запуск (не распаковывает каждый раз)
- Меньше триггерей антивируса
- Но: при каждом запуске антивирус всё равно сканирует содержимое архива

**one-file** (избегайте):
- Папка ~300 МБ распаковывается на диск → очень медленно
- Много файлов для проверки антивирусом → "долго"

### Минимальный набор библиотек

```python
excludes=[
    'matplotlib', 'scipy', 'IPython', 'notebook', 'pytest',
    'PIL', 'Image', 'tkinter.test',
    'pandas.tests', 'numpy.tests', 'numpy.f2py',
    'sqlite3', 'test', 'unittest', 'pydoc_data',
    'setuptools', 'pkg_resources', 'pip',
    'lxml', 'jinja2', 'pyarrow', 'odf', 'pyxlsb',
]
```

**Важно**: `numpy.typing` НЕ исключаем — pandas импортирует его на уровне модуля. Исключение приведёт к падению с `ModuleNotFoundError`.

---

## 📋 Чеклист перед публикацией подписанной сборки

- [ ] Сертификат валиден (не истёк, не заблокирован)
- [ ] `build.spec` содержит иконку (`icon='app.ico'`)
- [ ] Workflow собран на свежей ОС:
  - Windows: `windows-latest`
  - macOS: `macos-latest` (или `macos-14` для Apple Silicon)
- [ ] Логи сборки без ошибок/предупреждений
- [ ] Артефакты заархивированы:
  - `SIRSTAT-windows.zip` (папка с `.exe`)
  - `SIRSTAT-macos.zip` (папка с `.app`)

---

## 🐛 Решение частых проблем

### Проблема: «Windows SmartScreen всё равно предупреждает»

**Решение**:
1. Убедитесь, что подпись **EV-сертификатом**, а не OV
2. Проверьте `signtool verify` — нет ли ошибок валидации
3. Добавьте репозиторий в белый список антивируса (для CI)

### Проблема: «macOS Gatekeeper блокирует»

**Решение**:
1. Убедитесь, что `.app` подписан **Developer ID**, а неadhoc
2. Проверьте `spctl -a -v /путь/к/SIRSTAT.app` — должен показать "accepted"
3. Если adhoc-подпись: укажите в релизе инструкции для пользователя (см. выше)

### Проблема: «Антивирус блокирует сразу после запуска»

**Решение**:
1. Добавьте SHA-256 хэш файла в белый список антивируса
2. Обновите сигнатуры антивируса
3. Для корпоративных клиентов — настройте политику исключений через GPO/Microsoft Intune

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