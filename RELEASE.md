# Как собирать релизы

CI (`.github/workflows/build.yml`) собирает автономное приложение через PyInstaller
и публикует GitHub Release автоматически при создании тега вида `vX.Y.Z`.

## Выпуск новой версии

```bash
git checkout main && git pull
git tag v1.0.0
git push origin v1.0.0
```

После этого:
1. Вкладка **Actions → Build executable** соберёт приложения для Windows и macOS.
2. По завершении сборки job `release` создаст **GitHub Release** с файлами:
   - `SIRSTAT-windows.zip` (папка с `SIRSTAT.exe`),
   - `SIRSTAT-macos.zip` (`SIRSTAT.app`).

## Ручной запуск без релиза
Actions → «Build executable» → **Run workflow** — соберёт артефакты, но Release не создаст.

## Локальная сборка (для проверки)
```bash
pip install -r requirements.txt pyinstaller
pyinstaller build.spec --noconfirm
# результат: dist/SIRSTAT/
```

Замечания:
- Сборки не подписаны кодом подписи — Windows SmartScreen/macOS Gatekeeper могут
  предупреждать о неизвестном издателе (на macOS: правый клик → Открыть).
- Для своей иконки положите `app.ico`/`app.icns` в корень и укажите `icon=` в `build.spec`.
