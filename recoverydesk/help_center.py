"""Offline, six-language help for Tenshi 3.0.0.

The help text is deliberately about supported behavior, not a guarantee of
successful recovery. No filesystem or source device is opened by this module.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .i18n import LANGUAGES
from . import __version__
from .version_info import display_version

TOPICS = (
    'start', 'partitions', 'browser', 'imaging', 'export',
    'sessions', 'safety', 'diagnostics', 'about',
)

# Order: German, English, Spanish, Simplified Chinese, Russian, Japanese.
DATA = {
 'start': (
  ('Erste Schritte', 'Getting started', 'Primeros pasos', '入门指南', 'Начало работы', 'はじめに'),
  (
   '1. Öffne nach Möglichkeit ein zuvor erstelltes Image mit „Image auswählen“.\n\n2. Nach der Quellenauswahl öffnet Tenshi automatisch „Partitionen“ und beginnt die Schnellanalyse. Nutze die Tiefensuche nur bei Bedarf.\n\n3. Doppelklicke auf eine gefundene Partition, um „Dateien & Ordner“ zu öffnen und das Dateisystem einzulesen.\n\n4. Wähle Dateien oder Ordner aus und nutze „Export prüfen“, bevor du den grünen Stapel-Export startest.\n\n5. Speichere gerettete Dateien auf einem anderen physischen Datenträger.\n\nBei ungewöhnlichen Geräuschen, Aussetzern oder einem mechanischen Defekt weitere Zugriffe vermeiden und professionelle Hilfe erwägen.',
   '1. Prefer an existing disk image using “Select image”.\n\n2. After selecting a source, Tenshi opens “Partitions” and starts a quick scan automatically. Use deep scan only if necessary.\n\n3. Double-click a detected partition to open “Files & Folders” and scan the file system.\n\n4. Select files or folders and run “Check export” before the green batch export.\n\n5. Save recovered files to a different physical disk.\n\nIf a drive makes unusual noises, disconnects or has physical damage, avoid further reads and consider professional assistance.',
   '1. Abra preferentemente una imagen existente con «Seleccionar imagen».\n\n2. Al seleccionar un origen, Tenshi abre «Particiones» e inicia automáticamente el análisis rápido. Use el análisis profundo solo si es necesario.\n\n3. Haga doble clic en una partición para abrir «Archivos y carpetas» y leer el sistema de archivos.\n\n4. Seleccione archivos y use «Comprobar exportación» antes de la exportación por lotes.\n\n5. Guarde los datos en otro disco físico.\n\nSi hay ruidos extraños o daños físicos, evite nuevas lecturas y consulte a profesionales.',
   '1. 建议先通过“选择镜像”打开已有磁盘镜像。\n\n2. 选择数据源后，Tenshi 会自动打开“分区”并开始快速扫描；仅在必要时使用深度扫描。\n\n3. 双击找到的分区，切换到“文件与文件夹”并读取文件系统。\n\n4. 选中文件或文件夹，在批量导出前先运行“检查导出”。\n\n5. 将恢复的数据保存到另一块物理磁盘。\n\n如设备有异响、断连或物理损坏，请尽量避免继续读取并考虑专业协助。',
   '1. По возможности откройте готовый образ через «Выбрать образ».\n\n2. После выбора источника Tenshi автоматически открывает вкладку «Разделы» и запускает быстрый анализ. Глубокий поиск используйте при необходимости.\n\n3. Дважды щёлкните раздел для перехода к файлам и чтения файловой системы.\n\n4. Выберите файлы и выполните предварительную проверку перед пакетным экспортом.\n\n5. Сохраняйте данные на другом физическом диске.\n\nПри необычных звуках и аппаратных сбоях избегайте чтения и обратитесь к специалистам.',
   '1. 可能なら「イメージを選択」で既存のディスクイメージを開きます。\n\n2. ソースを選択すると Tenshi は「パーティション」を開き、クイックスキャンを自動で開始します。詳細スキャンは必要な場合のみ実行します。\n\n3. 検出したパーティションをダブルクリックして「ファイルとフォルダー」を開きます。\n\n4. ファイルを選択し、一括エクスポートの前に事前検査を実行します。\n\n5. 復旧先には別の物理ディスクを使用してください。\n\n異音、切断、物理的損傷がある場合は読み取りを控え、専門家への相談を検討してください。'
  )),
 'partitions': (
  ('Partitionen', 'Partitions', 'Particiones', '分区', 'Разделы', 'パーティション'),
  (
   'Wähle ein Image, einen physischen Datenträger oder ein logisches Laufwerk aus. Die Schnellanalyse startet automatisch und liest Partitions- und Dateisystemmetadaten. Die Tiefensuche kann mehr Bereiche lesen und länger dauern.\n\nGefundene Bootsektoren ohne gültige Partitionstabelle sind nur Kandidaten. Eine hohe Plausibilität beweist keine intakten Dateien.\n\nDurch Doppelklick auf einen Eintrag übernimmt Tenshi den Byte-Offset, öffnet „Dateien & Ordner“ und startet die Dateisystemanalyse. Ein einfacher Klick wählt nur aus.',
   'Select an image, physical disk or volume. Quick scan starts automatically and reads partition and file-system metadata; deep scan may read more and take longer.\n\nBoot-sector findings without a valid partition table are only candidates. High confidence does not prove file integrity.\n\nDouble-click a row to carry over the byte offset, switch to “Files & Folders” and start scanning. A single click only selects.',
   'Seleccione una imagen, disco físico o volumen. El análisis rápido se inicia automáticamente y examina metadatos; el análisis profundo puede leer más y tardar más.\n\nLos sectores de arranque sin tabla válida son candidatos. Una confianza alta no garantiza archivos íntegros.\n\nHaga doble clic para usar el desplazamiento correcto, cambiar al explorador y empezar el análisis. Un clic solo selecciona.',
   '请选择镜像、物理磁盘或卷。快速扫描自动开始，并读取分区和文件系统元数据；深度扫描会读取更多区域。\n\n没有有效分区表的引导扇区只能视为候选项。高可信度不代表文件内容完整。\n\n双击分区可传递字节偏移量、打开文件列表并开始读取；单击仅选中。',
   'Выберите образ, физический диск или том. Быстрый анализ запускается автоматически и читает метаданные; глубокий поиск может читать больше областей.\n\nЗагрузочные сектора без корректной таблицы — кандидаты. Высокая достоверность не означает целостность файлов.\n\nДвойной щелчок переносит смещение, открывает список файлов и запускает анализ; один щелчок только выделяет.',
   'イメージ、物理ディスク、ボリュームを選択するとクイックスキャンが自動で始まり、メタデータを読み、詳細スキャンはより多くの領域を調査します。\n\n有効なパーティションテーブルのないブートセクターは候補にすぎません。高い確度もファイルの完全性を保証しません。\n\nダブルクリックするとオフセットを引き継いでファイル画面へ移動し、解析を開始します。'
  )),
 'browser': (
  ('Dateien & Ordner', 'Files & folders', 'Archivos y carpetas', '文件与文件夹', 'Файлы и папки', 'ファイルとフォルダー'),
  (
   'Tenshi zeigt Dateien und Ordner für NTFS, FAT32, exFAT, ext2/3/4 und eingeschränkt Btrfs/XFS. Gelöschte Dateien sind abhängig vom Dateisystem teilweise rekonstruierbar; Btrfs/XFS-Löschhinweise sind nicht exportierbar.\n\nDie Suche kann nach Namen, Dateiendungen und Kategorien filtern. TMP-Dateien sind standardmäßig nur in der Ansicht verborgen; das ist keine Löschung.\n\nBei großen Ergebnislisten zeigt Tenshi maximal 750 Zeilen pro Seite. Strg+A wählt nur die sichtbare Seite. Eine rote Warnung kennzeichnet problematische Metadaten, nicht zwingend defekte Dateiinhalte.',
   'Browse NTFS, FAT32, exFAT, ext2/3/4 and limited Btrfs/XFS. Deleted-file recovery is partial; Btrfs/XFS deleted metadata hints cannot be exported.\n\nSearch by name, extension or category. TMP files are hidden from the view by default, not deleted.\n\nLarge lists show at most 750 rows per page; Ctrl+A selects the current page only. A warning indicates metadata concerns, not necessarily damaged content.',
   'Explore NTFS, FAT32, exFAT, ext2/3/4 y Btrfs/XFS con limitaciones. La recuperación de borrados es parcial; los indicios de Btrfs/XFS no se pueden exportar.\n\nBusque por nombre, extensión o categoría. Los TMP se ocultan en la vista, no se eliminan.\n\nSe muestran hasta 750 filas por página; Ctrl+A selecciona solo esa página. Una advertencia indica problemas de metadatos, no necesariamente del contenido.',
   '可浏览 NTFS、FAT32、exFAT、ext2/3/4 和有限支持的 Btrfs/XFS。已删除文件仅能部分恢复；Btrfs/XFS 的删除线索无法导出。\n\n可以按名称、扩展名和类别搜索。TMP 文件默认仅在界面中隐藏，并未删除。\n\n每页最多显示 750 行；Ctrl+A 仅选择当前页。警告表示元数据存在疑点，不一定代表内容损坏。',
   'Просмотр NTFS, FAT32, exFAT, ext2/3/4 и частично Btrfs/XFS. Восстановление удалённых файлов ограничено; подсказки Btrfs/XFS нельзя экспортировать.\n\nПоиск по имени, расширению и категории. TMP скрыты только в интерфейсе.\n\nДо 750 строк на странице; Ctrl+A выделяет лишь текущую страницу. Предупреждение относится к метаданным, а не обязательно к содержимому.',
   'NTFS、FAT32、exFAT、ext2/3/4、制限付きの Btrfs/XFS を表示します。削除ファイルの復旧は限定的で、Btrfs/XFS の削除メタデータは書き出せません。\n\n名前、拡張子、カテゴリで検索できます。TMP は表示上隠すだけで削除しません。\n\n1ページ最大750行で、Ctrl+A は表示中のページのみ選択します。警告はメタデータの問題を示し、内容の損傷を確定しません。'
  )),
 'imaging': (
  ('Image erstellen', 'Create an image', 'Crear imagen', '创建镜像', 'Создание образа', 'イメージの作成'),
  (
   '„Image erstellen / fortsetzen“ kopiert lesend von der Quelle in eine separate Image-Zieldatei. Beim Fortsetzen wird die bestehende Zieldatei weitergeschrieben. Statusdateien (.recovery.json/.journal) dienen zur sicheren Wiederaufnahme.\n\nBei bestätigten Medienfehlern sind 0–3 zusätzliche Leseversuche möglich. Jeder Versuch kann ein defektes Laufwerk belasten. „Nullen + protokollieren“ erstellt Datenlücken; „Sicher anhalten“ stoppt am letzten gültigen Prüfpunkt.\n\nZugriffsverweigerungen, Geräteabbrüche und unerwartet kurze Leseantworten sind keine bestätigten defekten Sektoren und führen zum Abbruch. Für mechanisch defekte Laufwerke professionelle schonende Verfahren bevorzugen.',
   '“Create / resume image” reads the source into a separate image file. Resume extends the existing destination; .recovery.json/.journal files hold checkpoints.\n\nFor confirmed media errors, 0–3 retries are available. Each read can stress failing hardware. Zero fill records missing data; safe stop preserves the last valid checkpoint.\n\nPermission failures, disconnected devices and unexpected short reads stop the operation rather than being counted as bad sectors. Prefer specialist low-impact imaging for failing hardware.',
   '«Crear / reanudar imagen» copia la fuente a otra imagen. Al reanudar continúa escribiendo en el archivo de destino; .recovery.json/.journal guardan el estado.\n\nAnte errores del medio confirmados hay 0–3 reintentos, que pueden dañarlo más. Rellenar con ceros deja datos ausentes; la parada segura conserva el último punto válido.\n\nPermisos denegados, desconexiones y lecturas cortas inesperadas detienen el proceso. Para discos dañados, prefiera herramientas especializadas.',
   '“创建／继续镜像”只读访问源并写入单独的目标镜像。续传时继续写入现有文件；.recovery.json/.journal 用于恢复。\n\n确认的介质错误可重试 0–3 次，但每次读取都可能加重损坏。填零会留下数据缺口；安全停止会保留最后有效检查点。\n\n拒绝访问、设备断开和异常短读会终止操作，不会当作坏扇区。故障硬盘建议使用专业低负载工具。',
   '«Создать / продолжить образ» читает источник и записывает отдельный файл образа. При возобновлении файл дописывается; .recovery.json/.journal хранят контрольные точки.\n\nДля подтверждённых ошибок носителя предусмотрено 0–3 повтора. Они могут ухудшить состояние диска. Нулевое заполнение означает потерю данных; безопасная остановка сохраняет контрольную точку.\n\nОтказ в доступе, отключение и короткие ответы вызывают остановку. При аппаратных повреждениях применяйте специализированные средства.',
   '「イメージ作成／再開」は元ディスクを読み、別のイメージファイルへ書き込みます。再開時は既存ファイルへ追記し、.recovery.json/.journal に状態を保存します。\n\n確定した媒体エラーのみ0～3回の再試行が可能ですが、故障を悪化させる恐れがあります。ゼロ埋めは欠損を残し、安全停止は有効なチェックポイントを保持します。\n\nアクセス拒否、切断、短い読み取りは停止します。故障媒体には専門的な手法を推奨します。'
  )),
 'export': (
  ('Stapel-Export', 'Batch export', 'Exportación por lotes', '批量导出', 'Пакетный экспорт', '一括エクスポート'),
  (
   'Wähle rechts Dateien oder Ordner. „Export prüfen“ bewertet Dateisystem-Metadaten, ohne den gesamten Inhalt zu lesen. „Bereit“ bedeutet nicht, dass die Datei intakt ist. Nachgewiesene NTFS-Zuordnungskonflikte werden gesperrt.\n\nDer grüne Button „Stapel-Export / fortsetzen“ exportiert in ein separates Ziel auf einem anderen physischen Datenträger. Bestehende fremde Dateien werden nicht überschrieben.\n\nBei Wiederaufnahme prüft Tenshi vollständige bereits exportierte Dateien per SHA-256. Eine unterbrochene Einzeldatei wird neu begonnen. Verborgene TMP-Dateien können bei einem rekursiven Ordnerexport enthalten sein.',
   'Select files or folders. “Check export” inspects metadata but not full file contents; “Ready” never guarantees integrity. Proven NTFS mapping conflicts are blocked.\n\nUse the green batch export button to write to another physical disk. Untracked existing files are never overwritten.\n\nResume verifies completed outputs with SHA-256; a partially exported file restarts. Hidden TMP files may still be included in recursive folder exports.',
   'Seleccione archivos o carpetas. «Comprobar exportación» examina metadatos, no el contenido completo; «Listo» no garantiza integridad. Los conflictos NTFS confirmados se bloquean.\n\nLa exportación por lotes guarda en otro disco físico y no sobrescribe archivos ajenos.\n\nAl reanudar se verifican con SHA-256 las salidas completas; el archivo incompleto se reinicia. Los TMP ocultos pueden incluirse al exportar carpetas.',
   '选中文件或文件夹。“检查导出”仅检查元数据，不验证完整内容；“就绪”不保证文件完好。已证实的 NTFS 映射冲突会被阻止。\n\n绿色批量导出按钮将文件写入另一块物理磁盘，不覆盖现有的外部文件。\n\n恢复任务时用 SHA-256 验证已完成文件，未完成的单个文件需重新导出。递归导出文件夹可能包含隐藏的 TMP 文件。',
   'Выберите файлы или папки. Предварительная проверка оценивает метаданные, но не содержимое; «Готово» не означает целостность. Подтверждённые конфликты NTFS блокируются.\n\nЗелёная кнопка экспорта сохраняет файлы на другой физический диск без перезаписи чужих файлов.\n\nВозобновление проверяет завершённые файлы по SHA-256, незавершённый файл начинается заново. Скрытые TMP могут попасть в экспорт папок.',
   'ファイルまたはフォルダーを選択します。事前検査はメタデータのみ確認し、内容の完全性は保証しません。確認された NTFS の割り当て競合はブロックされます。\n\n緑の一括エクスポートで別の物理ディスクに保存します。既存の無関係なファイルは上書きしません。\n\n再開時は完了ファイルを SHA-256 で検証し、未完了のファイルは再実行します。フォルダーの再帰的な書き出しには非表示の TMP が含まれる場合があります。'
  )),
 'sessions': (
  ('Analysesitzungen', 'Analysis sessions', 'Sesiones de análisis', '分析会话', 'Сеансы анализа', '解析セッション'),
  (
   'Im Menü „Analysesitzung“ kannst du bereits eingelesene Partitions- und Dateimetadaten speichern. Sitzungen sind nur für reguläre Image-Dateien verfügbar, nicht für physische Datenträger.\n\nBeim Laden prüft Tenshi Größe, Änderungszeit und mehrere SHA-256-Proben des Images. Das ist keine vollständige Hashprüfung: Nicht beprobte Änderungen sind möglich.\n\nEine .tenshi-session enthält Metadaten und kann private Datei- und Ordnernamen enthalten. Sie ist kein Backup von Dateiinhalten. Bewahre Sitzungsdateien geschützt auf.',
   '“Analysis session” saves scanned partition and file metadata for regular image files only; physical drives are not supported.\n\nLoading checks image size, modification time and several SHA-256 samples. This is not a full-file verification and cannot rule out unobserved changes.\n\nA .tenshi-session contains metadata and may include private names. It does not back up recovered file contents; store it securely.',
   '«Sesión de análisis» guarda metadatos de imágenes normales, no de discos físicos.\n\nAl cargar verifica tamaño, fecha y varias muestras SHA-256, no la imagen completa; pueden escapar cambios.\n\nEl archivo .tenshi-session puede contener nombres privados. No es copia de seguridad de datos; guárdelo de forma segura.',
   '“分析会话”仅保存普通镜像文件的分区和文件元数据，不支持物理磁盘会话。\n\n加载时检查文件大小、修改时间和多个 SHA-256 样本，并非全量验证。\n\n.tenshi-session 可能包含私人文件名，不含恢复的文件内容，需妥善保管。',
   '«Сеанс анализа» сохраняет метаданные обычных файлов образов, не физических дисков.\n\nПри загрузке сверяются размер, время изменения и выборочные SHA-256, но не весь файл.\n\n.tenshi-session может содержать частные имена файлов. Это не резервная копия содержимого; храните файл защищённо.',
   '「解析セッション」は通常のイメージファイルのメタデータを保存します。物理ディスクには対応しません。\n\n読み込み時にサイズ、更新日時、複数の SHA-256 サンプルを照合しますが、全体の検証ではありません。\n\n.tenshi-session には個人情報を含むファイル名が保存される可能性があり、復旧データのバックアップではありません。'
  )),
 'safety': (
  ('Sicherheit & Grenzen', 'Safety & limitations', 'Seguridad y límites', '安全与限制', 'Безопасность и ограничения', '安全性と制限'),
  (
   'Tenshi öffnet Quelldatenträger nur lesend; Images, Statusdateien, Exporte und Protokolle werden ausschließlich an den jeweiligen Zielorten geschrieben. Schreibgeschützt bedeutet nicht, dass physisch defekte Hardware durch das Lesen nicht weiter belastet wird.\n\nStatus „Bereit“, gefundene Dateinamen und erfolgreiche Exporte sind keine Garantie für vollständige oder unbeschädigte Inhalte. Gelöschte Daten können längst überschrieben sein. Btrfs/XFS-Löschhinweise können nicht exportiert werden.\n\nNutze zuerst Kopien oder selbst erstellte Testimages und halte die Originaldaten unverändert. Bei wertvollen Daten und ernsthaften Hardwaredefekten professionelle Hilfe in Betracht ziehen.',
   'Tenshi opens source disks read-only. Images, checkpoints, exports and diagnostics are written to their respective destinations. Read-only operations can still stress damaged hardware.\n\n“Ready”, visible filenames and successful exports cannot guarantee intact data. Deleted clusters may have been reused. Btrfs/XFS deletion hints cannot be exported.\n\nWork on copies or test images first and leave originals unchanged. Consider professional recovery for valuable data and physical damage.',
   'Tenshi abre el origen en modo de solo lectura. Las imágenes, estados, exportaciones y registros se escriben en sus destinos. Incluso leer puede perjudicar el hardware defectuoso.\n\n«Listo», nombres visibles y exportaciones correctas no garantizan datos íntegros. Los sectores borrados pueden estar reutilizados. Los indicios Btrfs/XFS no se exportan.\n\nTrabaje primero con copias y mantenga el original sin cambios; consulte a especialistas ante daños graves.',
   'Tenshi 以只读方式打开源磁盘；镜像、状态、导出和日志仅写入指定目标。但读取仍可能加重物理损坏。\n\n“就绪”、可见文件名和成功导出都不保证内容完好。已删除的数据区域可能被重用。Btrfs/XFS 删除线索无法导出。\n\n优先使用副本或测试镜像，保护原始数据。重要数据和物理故障建议寻求专业帮助。',
   'Tenshi открывает источник только для чтения; образы, состояния, экспорт и журналы записываются в выбранные места. Даже чтение опасно для повреждённого оборудования.\n\nСтатус «Готово» и успешный экспорт не гарантируют сохранность данных. Удалённые блоки могли быть перезаписаны. Подсказки Btrfs/XFS не экспортируются.\n\nНачинайте с копий и не изменяйте оригинал. При серьёзных повреждениях обратитесь к специалистам.',
   'Tenshi は元ディスクを読み取り専用で開き、イメージ、状態、エクスポート、ログは保存先へ書き込みます。ただし読み取りでも故障を悪化させる場合があります。\n\n「準備完了」やエクスポートの成功は内容の完全性を保証しません。削除領域は上書きされている可能性があります。Btrfs/XFS の削除情報は書き出せません。\n\nまずコピーやテストイメージを用い、元データを保持してください。重大な故障は専門家へ相談してください。'
  )),
 'diagnostics': (
  ('Fehlerdiagnose', 'Troubleshooting', 'Solución de problemas', '故障排查', 'Устранение неполадок', 'トラブルシューティング'),
  (
   'Mit „Fehlerprotokoll“ (oben rechts) öffnest du die technischen Meldungen. Die Datei liegt unter Windows normalerweise in %LOCALAPPDATA%\\Tenshi\\Logs. Veröffentliche Protokolle erst nach Prüfung auf private Pfade.\n\nBei Build-Problemen prüfe tenshi-build.log und führe check_windows.bat aus. run_tests.bat startet die Tests separat; dabei absichtlich erzeugte Fehler können protokolliert werden.\n\nFür die EXE wird 64-Bit-Python ab 3.11 und PyInstaller benötigt. Der Quellcode enthält kein fertig gebautes Windows-Programm. Treten echte Laufwerksfehler auf, greife nicht wiederholt auf ein verdächtig beschädigtes Medium zu.',
   'Open “Error log” (top right) to inspect technical records, normally stored under %LOCALAPPDATA%\\Tenshi\\Logs on Windows. Review logs for private paths before sharing.\n\nFor build failures check tenshi-build.log and run check_windows.bat. run_tests.bat runs tests separately; intentionally simulated failures may be logged.\n\nA Windows EXE requires 64-bit Python 3.11+ and PyInstaller. Source packages do not contain prebuilt binaries. Do not keep retrying reads on suspected failing media.',
   'Abra «Registro de errores» para ver los mensajes técnicos en %LOCALAPPDATA%\\Tenshi\\Logs. Revise si hay rutas privadas antes de compartir.\n\nPara errores de compilación consulte tenshi-build.log y check_windows.bat. run_tests.bat ejecuta los tests por separado; algunos simulan errores.\n\nLa EXE requiere Python de 64 bits 3.11+ y PyInstaller. El código fuente no incluye una EXE compilada. Evite nuevas lecturas en discos defectuosos.',
   '点击右上角“错误日志”查看技术记录，Windows 中通常位于 %LOCALAPPDATA%\\Tenshi\\Logs。分享前请检查私人路径。\n\n构建失败请查看 tenshi-build.log 并运行 check_windows.bat。run_tests.bat 单独执行测试；部分测试会模拟错误。\n\n构建 EXE 需要 64 位 Python 3.11+ 和 PyInstaller。源码包不包含预编译程序。疑似硬件故障时避免反复读取。',
   '«Журнал ошибок» показывает технические записи в %LOCALAPPDATA%\\Tenshi\\Logs. Перед отправкой проверьте наличие личных путей.\n\nПри проблемах сборки откройте tenshi-build.log и запустите check_windows.bat. run_tests.bat выполняет тесты отдельно; часть ошибок моделируется намеренно.\n\nEXE требует 64-битный Python 3.11+ и PyInstaller. Исходный архив не содержит готового EXE. Не повторяйте чтение неисправных дисков.',
   '右上の「エラーログ」で技術記録を確認できます。Windows では通常 %LOCALAPPDATA%\\Tenshi\\Logs に保存されます。共有前に個人情報が含まれていないか確認してください。\n\nビルドの問題は tenshi-build.log と check_windows.bat を確認します。run_tests.bat は別途テストを実行し、意図的なエラーが記録されることもあります。\n\nEXE の作成には64ビット Python 3.11+ と PyInstaller が必要です。ソース配布には EXE は含まれません。故障媒体の再読み取りは控えてください。'
  )),
 'about': (
  ('Über Tenshi', 'About Tenshi', 'Acerca de Tenshi', '关于 Tenshi', 'О программе Tenshi', 'Tenshi について'),
  (
   'Tenshi {version} – Datenrettung und schreibgeschützte Analyse für Windows 10/11 (64 Bit).\n\nDieses Programm ist experimentelle Freeware. Unterstützte Funktionen und Grenzen sind in der Hilfe und README beschrieben. Getestete synthetische Images ersetzen keine Prüfung mit echter Hardware.\n\nWindows-Build, Installer, Laufwerkszugriffe und Datenrettung auf echten Medien müssen vor einer öffentlichen Freigabe separat validiert werden. Eine bestandene Testsuite ist keine Zertifizierung.\n\nDas Programm führt keine Dateisystemreparatur am Quelldatenträger durch.',
   'Tenshi {version} – read-only data recovery and analysis for Windows 10/11 (64-bit).\n\nThis is experimental freeware. Capabilities and limitations are documented in the help and README. Synthetic image tests do not replace real-hardware validation.\n\nWindows builds, installer, physical-drive access and real recovery must be validated before a public release. Passing automated tests is not certification.\n\nTenshi does not repair the source filesystem.',
   'Tenshi {version}: recuperación y análisis de solo lectura para Windows 10/11 de 64 bits.\n\nSoftware gratuito experimental. Las pruebas con imágenes sintéticas no sustituyen las pruebas con hardware real.\n\nAntes de publicar deben verificarse en Windows la EXE, el instalador, el acceso a discos y la recuperación real. Superar los tests no es una certificación.\n\nTenshi no repara el sistema de archivos de origen.',
   'Tenshi {version}：适用于 Windows 10/11（64 位）的只读数据恢复与分析工具。\n\n本程序为实验性免费软件。模拟镜像测试不能取代真实硬件验证。\n\n公开发布前仍需在 Windows 上验证 EXE、安装程序、物理设备访问和实际数据恢复。通过自动测试并非认证。\n\nTenshi 不会修复源文件系统。',
   'Tenshi {version} — экспериментальная бесплатная программа для анализа и восстановления данных в Windows 10/11 (64 бит).\n\nТесты синтетических образов не заменяют реальную проверку оборудования.\n\nПеред публичным выпуском необходимы испытания EXE, установщика, дискового доступа и восстановления данных в Windows. Успешные тесты не являются сертификацией.\n\nTenshi не исправляет исходную файловую систему.',
   'Tenshi {version} — Windows 10/11（64ビット）向けの読み取り専用データ復旧・解析ツールです。\n\n実験的なフリーウェアであり、合成イメージのテストだけでは実機検証になりません。\n\n一般公開前に Windows で EXE、インストーラ、物理ディスク読み取り、実際の復旧を検証する必要があります。自動テストの成功は認証ではありません。\n\n元のファイルシステムを修復する機能はありません。'
  )),
}

LANG_INDEX = {code: i for i, code in enumerate(LANGUAGES)}


def topic_text(topic: str, language: str) -> tuple[str, str]:
    """The complete topic text; never fall back to a misleading other topic."""
    if topic not in DATA:
        raise ValueError('Unknown help topic')
    lang = LANG_INDEX.get(language, 0)
    labels, bodies = DATA[topic]
    return labels[lang], bodies[lang].format(version=display_version())


def available_topics(language: str, query: str = '') -> list[str]:
    needle = query.strip().casefold()
    return [t for t in TOPICS if not needle or needle in '\n'.join(topic_text(t, language)).casefold()]


WINDOW_LABELS = {
 'de': ('Tenshi – Hilfe', 'Suchen:', 'Zum Hauptregister wechseln', 'Schließen', 'Keine passenden Themen.'),
 'en': ('Tenshi – Help', 'Search:', 'Go to main tab', 'Close', 'No matching topics.'),
 'es': ('Tenshi – Ayuda', 'Buscar:', 'Ir a la pestaña principal', 'Cerrar', 'No hay temas coincidentes.'),
 'zh': ('Tenshi – 帮助', '搜索：', '切换到主选项卡', '关闭', '没有匹配的主题。'),
 'ru': ('Tenshi – Справка', 'Поиск:', 'Перейти на основную вкладку', 'Закрыть', 'Темы не найдены.'),
 'ja': ('Tenshi – ヘルプ', '検索:', 'メインタブに移動', '閉じる', '一致する項目がありません。'),
}


class HelpWindow(tk.Toplevel):
    """Nonmodal, searchable local help. Never opens disks or starts scans."""
    def __init__(self, app, topic='start'):
        super().__init__(app)
        self.app = app
        self.language = app.language
        self.topic = topic if topic in TOPICS else 'start'
        self.geometry('890x610')
        self.minsize(650, 430)
        self.search_var = tk.StringVar(master=self)
        container = ttk.Frame(self, padding=12)
        container.pack(fill='both', expand=True)
        bar = ttk.Frame(container)
        bar.pack(fill='x', pady=(0, 10))
        self.search_label = ttk.Label(bar)
        self.search_label.pack(side='left')
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=8)
        self.search_var.trace_add('write', self._search_changed)
        content = ttk.Frame(container)
        content.pack(fill='both', expand=True)
        self.topics_list = tk.Listbox(content, exportselection=False, width=29, activestyle='dotbox',
                                      font=('Segoe UI', 10))
        self.topics_list.pack(side='left', fill='y', padx=(0, 10))
        self.topics_list.bind('<<ListboxSelect>>', self._topic_selected)
        right = ttk.Frame(content)
        right.pack(side='left', fill='both', expand=True)
        self.title_label = ttk.Label(right, font=('Segoe UI', 15, 'bold'))
        self.title_label.pack(anchor='w', pady=(0, 10))
        content_text = ttk.Frame(right)
        content_text.pack(fill='both', expand=True)
        self.body_text = tk.Text(content_text, wrap='word', font=('Segoe UI', 11),
                                padx=12, pady=12, relief='flat', takefocus=True)
        scroll = ttk.Scrollbar(content_text, orient='vertical', command=self.body_text.yview)
        self.body_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.body_text.pack(side='left', fill='both', expand=True)
        footer = ttk.Frame(container)
        footer.pack(fill='x', pady=(10, 0))
        self.go_button = ttk.Button(footer, command=self._go_to_tab)
        self.go_button.pack(side='left')
        self.close_button = ttk.Button(footer, command=self.destroy)
        self.close_button.pack(side='right')
        self._visible_topics = []
        self.bind('<Escape>', lambda _: self.destroy())
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.refresh_language(self.language)

    def _search_changed(self, *_):
        self._update_topics()

    def _update_topics(self):
        self._visible_topics = available_topics(self.language, self.search_var.get())
        self.topics_list.delete(0, 'end')
        for code in self._visible_topics:
            title, _ = topic_text(code, self.language)
            self.topics_list.insert('end', title)
        if not self._visible_topics:
            self.title_label.configure(text='')
            self._show_body(WINDOW_LABELS[self.language][4])
            self.go_button.configure(state='disabled')
            return
        if self.topic not in self._visible_topics:
            self.topic = self._visible_topics[0]
        position = self._visible_topics.index(self.topic)
        self.topics_list.selection_set(position)
        self.topics_list.activate(position)
        self._display_topic()

    def _show_body(self, content):
        self.body_text.configure(state='normal')
        self.body_text.delete('1.0', 'end')
        self.body_text.insert('1.0', content)
        self.body_text.configure(state='disabled')
        self.body_text.yview_moveto(0)

    def _display_topic(self):
        title, content = topic_text(self.topic, self.language)
        self.title_label.configure(text=title)
        self._show_body(content)
        self.go_button.configure(state='normal' if self.topic in ('partitions','browser') else 'disabled')

    def _topic_selected(self, event=None):
        selection = self.topics_list.curselection()
        if selection and selection[0] < len(self._visible_topics):
            self.topic = self._visible_topics[selection[0]]
            self._display_topic()

    def _go_to_tab(self):
        tab = 'partition' if self.topic == 'partitions' else 'files'
        self.app._select_main_tab(tab)
        self.app.lift()

    def refresh_language(self, language):
        self.language = language if language in LANGUAGES else 'de'
        title, search, go, close, _ = WINDOW_LABELS[self.language]
        self.title(title)
        self.search_label.configure(text=search)
        self.go_button.configure(text=go)
        self.close_button.configure(text=close)
        self._update_topics()
        self.refresh_theme()

    def refresh_theme(self):
        colors = self.app._palette()
        for widget in (self.topics_list, self.body_text):
            widget.configure(bg=colors['input'], fg=colors['text'],
                             selectbackground=colors['select'], selectforeground=colors['text'])
