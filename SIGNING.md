# Подпись сборок (код-сайнинг)

Workflow `.github/workflows/build.yml` умеет автоматически подписывать исполняемые
файлы. Пока секреты не добавлены, сборки выходят **неподписанными** (Windows
SmartScreen и антивирусы могут предупреждать). Чтобы убрать предупреждения,
нужны платные сертификаты — их выпускают аккредитованные CA.

## 1. Windows — Authenticode (EV или OV код-сертификат)

Что понадобится: сертификат **Code Signing** (DigiCert, Sectigo, GlobalSign,
SSL.com и др.; для полного доверия SmartScreen без «репутации» лучше EV-сертификат;
многие CA сейчас выдают его в облачном HSM — тогда подпись выполняется через их
CLI/REST, а не обычным `signtool`).

После получения PFX-файла создайте в репозитории
(Settings → Secrets and variables → Actions → New repository secret):

| Secret | Значение |
|---|---|
| `WIN_CODESIGN_P12_BASE64` | PFX, закодированный в base64: `base64 -w0 cert.p12` (Linux/macOS) или `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.p12"))` (PowerShell) |
| `WIN_CODESIGN_PASSWORD`   | пароль от PFX |

Workflow импортирует сертификат во временное хранилище раннера и подпишет
`SIRSTAT.exe` и все DLL из `dist/` (`signtool`, SHA-256 + timestamp).
Секретов нет → шаг пропускается.

## 2. macOS — Developer ID + notarization

Нужен аккаунт Apple Developer Program ($99/год) и сертификат
**Developer ID Application**, экспортированный в .p12 вместе с приватным ключом.

| Secret | Значение |
|---|---|
| `MAC_INSTALLER_CERT_BASE64`  | .p12 в base64 (`base64 < devID.p12`) |
| `MAC_INSTALLER_CERT_PASSWORD`| пароль от .p12 |
| `MAC_KEYCHAIN_PASSWORD`      | любой временный пароль для keychain на раннере |
| `APPLE_ID`                   | email аккаунта разработчика |
| `APPLE_APP_PASSWORD`         | app-specific password (appleid.apple.com → Sign-In and Security) |
| `APPLE_TEAM_ID`              | Team ID (Account → Membership) |

Workflow импортирует сертификат во временный keychain, подпишет бандл с
hardened runtime (права — `macos-entitlements.plist`) и отправит его на
нотаризацию Apple (`notarytool submit --wait`, затем `stapler staple`).
Подписанные+занотаризованные сборки Gatekeeper принимает без предупреждений.

## 3. Бесплатная альтернатива для macOS

Если нет Apple Developer: можно оставить ad-hoc подпись, но пользователю
придётся снимать quarantine вручную (`xattr -dr com.apple.quarantine ...`) —
это уже описано в тексте релиза.

## 4. Что ещё снижает «ругань» антивирусов

* Подпись выше — основной фактор.
* Сборка one-dir (не self-extracting one-file): fewer heuristics-триггеры, плюс
  быстрый старт (см. ниже про производительность).
* Минимальный набор библиотек в сборке (excludes в `build.spec`).
* Публикация только через GitHub Releases с указанием автора/назначения.

## Долгий запуск: что сделано

* Переход с one-file на **one-dir**: one-file при каждом старте распаковывает
  ~150–300 МБ во временную папку (антивирус проверяет каждый файл) — это и есть
  основная причина «очень долго». One-dir запускается сразу.
* Расширенные `excludes` в `build.spec`: из сборки исключены PIL, sqlite3,
  unittest, setuptools/pip, pandas/numpy тесты и пр. — меньше размер и быстрее
  импорт.
* Убран `xlrd` из зависимостей сборки (приложение читает .xlsx через openpyxl).

Ожидаемо: запуск подписанной one-dir сборки — единицы секунд вместо минут.
