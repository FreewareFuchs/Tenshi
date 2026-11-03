"""Offline, six-language help for Tenshi.

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
   ("1. Öffne nach Möglichkeit ein zuvor erstelltes Image mit „Image auswählen“.\n\n"
    "2. Nach der Quellenauswahl öffnet Tenshi automatisch „Partitionen“ und beginnt die Schnellanalyse. Nutze die Tiefensuche nur bei Bedarf.\n\n"
    "3. Doppelklicke auf eine gefundene Partition, um „Dateien & Ordner“ zu öffnen und das Dateisystem einzulesen.\n\n"
    "4. Wähle Dateien oder Ordner aus und nutze „Export prüfen“, bevor du den Stapel-Export startest.\n\n"
    "5. Speichere gerettete Dateien auf einem anderen physischen Datenträger.\n\n"
    "Bei ungewöhnlichen Geräuschen, Aussetzern oder einem mechanischen Defekt weitere Zugriffe vermeiden und professionelle Hilfe erwägen.\n\n"
    "Beim Schließen des Hauptfensters fragt Tenshi nach, wenn noch Export-, Image- oder Speichervorgänge laufen. Bei „Nein“ bleibt der bisherige Ausführungs- oder Pausenzustand erhalten. „Ja“ fordert die kontrollierte Unterbrechung an und wartet auf laufende Schreibvorgänge. Abschlussfehler werden vor dem Schließen angezeigt; im Leerlauf ist keine Rückfrage nötig."),
   ("1. Prefer an existing disk image using “Select image”.\n\n"
    "2. After selecting a source, Tenshi opens “Partitions” and starts a quick scan automatically. Use deep scan only if necessary.\n\n"
    "3. Double-click a detected partition to open “Files & Folders” and scan the file system.\n\n"
    "4. Select files or folders and run “Check export” before starting batch export.\n\n"
    "5. Save recovered files to a different physical disk.\n\n"
    "If a drive makes unusual noises, disconnects or has physical damage, avoid further reads and consider professional assistance.\n\n"
    "Closing the main window asks for confirmation while export, imaging or saves are active. “No” leaves jobs running or paused. “Yes” requests controlled interruption and waits for active writes. Completion errors are shown before closing; an idle application closes without asking."),
   ("1. Abra preferentemente una imagen existente con «Seleccionar imagen».\n\n"
    "2. Al seleccionar un origen, Tenshi abre «Particiones» e inicia automáticamente el análisis rápido. Use el análisis profundo solo si es necesario.\n\n"
    "3. Haga doble clic en una partición para abrir «Archivos y carpetas» y leer el sistema de archivos.\n\n"
    "4. Seleccione archivos y use «Comprobar exportación» antes de la exportación por lotes.\n\n"
    "5. Guarde los datos en otro disco físico.\n\n"
    "Si hay ruidos extraños o daños físicos, evite nuevas lecturas y consulte a profesionales.\n\n"
    "Al cerrar la ventana principal se pide confirmación si hay exportaciones, imágenes o guardados activos. «No» los deja en ejecución o en pausa. «Sí» solicita una interrupción controlada y espera las escrituras. Los errores se muestran antes de cerrar; en reposo no se pregunta."),
   ("1. 建议先通过“选择镜像”打开已有磁盘镜像。\n\n"
    "2. 选择数据源后，Tenshi 会自动打开“分区”并开始快速扫描；仅在必要时使用深度扫描。\n\n"
    "3. 双击找到的分区，切换到“文件与文件夹”并读取文件系统。\n\n"
    "4. 选中文件或文件夹，在批量导出前先运行“检查导出”。\n\n"
    "5. 将恢复的数据保存到另一块物理磁盘。\n\n"
    "如设备有异响、断连或物理损坏，请尽量避免继续读取并考虑专业协助。\n\n"
    "关闭主窗口时，如果仍有导出、镜像或保存任务，Tenshi 会请求确认。“否”保持任务运行或暂停；“是”请求有序中断并等待写入结束。结束时的错误会在关闭前显示；空闲时直接关闭。"),
   ("1. По возможности откройте готовый образ через «Выбрать образ».\n\n"
    "2. После выбора источника Tenshi автоматически открывает вкладку «Разделы» и запускает быстрый анализ. Глубокий поиск используйте при необходимости.\n\n"
    "3. Дважды щёлкните раздел для перехода к файлам и чтения файловой системы.\n\n"
    "4. Выберите файлы и выполните предварительную проверку перед пакетным экспортом.\n\n"
    "5. Сохраняйте данные на другом физическом диске.\n\n"
    "При необычных звуках и аппаратных сбоях избегайте чтения и обратитесь к специалистам.\n\n"
    "При закрытии главного окна с активным экспортом, созданием образа или сохранением требуется подтверждение. «Нет» оставляет задания работающими или на паузе. «Да» запрашивает контролируемую остановку и ждёт завершения записи. Ошибки показываются до закрытия; в покое подтверждение не требуется."),
   ("1. 可能なら「イメージを選択」で既存のディスクイメージを開きます。\n\n"
    "2. ソースを選択すると Tenshi は「パーティション」を開き、クイックスキャンを自動で開始します。詳細スキャンは必要な場合のみ実行します。\n\n"
    "3. 検出したパーティションをダブルクリックして「ファイルとフォルダー」を開きます。\n\n"
    "4. ファイルを選択し、一括エクスポートの前に事前検査を実行します。\n\n"
    "5. 復旧先には別の物理ディスクを使用してください。\n\n"
    "異音、切断、物理的損傷がある場合は読み取りを控え、専門家への相談を検討してください。\n\n"
    "エクスポート、イメージ作成、保存が動作中にメインウィンドウを閉じると確認します。「いいえ」は実行中・一時停止の状態を維持し、「はい」は制御された中断を要求して書き込み完了を待ちます。終了時のエラーは閉じる前に表示し、待機中は確認なしで終了します。"),
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
   'Tenshi zeigt Dateien und Ordner für NTFS, FAT32, exFAT, ext2/3/4 und eingeschränkt Btrfs/XFS. Gelöschte Dateien sind abhängig vom Dateisystem teilweise rekonstruierbar; Btrfs/XFS-Löschhinweise sind nicht exportierbar.\n\nDie Suche kann nach Namen, Dateiendungen und Kategorien filtern. TMP-Dateien sind standardmäßig nur in der Ansicht verborgen; das ist keine Löschung.\n\nBei großen Ergebnislisten zeigt Tenshi maximal 750 Zeilen pro Seite. Strg+A wählt nur die sichtbare Seite. Eine rote Warnung kennzeichnet problematische Metadaten, nicht zwingend defekte Dateiinhalte.\n\nDie Vorschau zeigt jetzt JPEG-, PNG-, BMP- und GIF-Bilder verkleinert und bei PDFs die erste Seite. Weitere PDF-Seiten sowie weitere Bilder einer Animation sind dabei nicht geprüft. Für DOCX kann ein begrenzter Textauszug erscheinen; eine Office-Seitendarstellung ist nicht enthalten.\n\nIm Dialog „Datei prüfen“ ergänzt „Inhalt prüfen“ die bisherige Leseprüfung: Bilddaten werden dekodiert, bei PDFs wird die erste Seite gerendert, bei DOCX/XLSX/PPTX werden ZIP-Prüfsummen und XML-Strukturen geprüft. Struktur lesbar bestätigt keine vollständigen Originalinhalte. Links, Makros und Dokumentaktionen werden nicht ausgeführt.\n\nErweiterte Vorschau und Inhaltsprüfung lesen höchstens 32 MiB je Datei. Bilder sind auf 20 Millionen Pixel begrenzt; XML-, Archiv-, Zeit- und Speichergrenzen können die Prüfung beenden. Prüfgrenze erreicht oder Nicht geprüft beweist keine Beschädigung. Geschützte Dokumente werden nicht entschlüsselt. Die Quelle bleibt schreibgeschützt; möglichst mit einem Image arbeiten.\n\nFür mehrere Dateien die gewünschten Einträge gemeinsam auswählen und Vorschau öffnen. Zurück und Weiter blättern innerhalb dieser Auswahl; die Positionsanzeige zeigt die aktuelle Datei. Ordner werden ausgelassen. Die Auswahl und ihre Quelle bleiben für dieses Fenster erhalten, auch wenn die Hauptansicht später geändert wird. Nicht darstellbare Dateien zeigen einen Hinweis und können weitergeblättert werden. An den Enden ist die jeweilige Richtung gesperrt. Es gibt keinen automatischen Dateiwechsel. Beim Wechsel wird die vorherige Verarbeitung abgebrochen; verspätete Ergebnisse werden verworfen.\n\nDateisignaturen suchen: Im Reiter „Dateisignaturen“ startet ein eigener Knopf die Suche nach Bildern, Office-Dateien, Archiven, Audio oder Video. Erkannt werden JPEG, PNG, BMP, GIF, TIFF und WebP; DOCX/XLSX/PPTX sowie ODF-Pakete; ZIP, 7z und TAR; WAV, MP3 mit ID3v2 und Ogg/Opus; AVI und MP4. Klassische Office-Dateien wie DOC/XLS/PPT und RAR werden noch nicht unterstützt. Das reguläre Image wird vollständig schreibgeschützt durchsucht; der Partitionsoffset wird ignoriert. Funde sind zusammenhängende Strukturkandidaten ohne Originalnamen, Ordner oder Löschstatus. Sie können Vorschau, Inhaltsprüfung und Export verwenden, bestätigen aber keine vollständigen Originalinhalte. Fragmente werden nicht zusammengesetzt. Größen- und Kandidatengrenzen können Ergebnisse unvollständig machen. Ein gespeicherter Exportauftrag durchsucht das Image beim Fortsetzen erneut.',
   'Browse NTFS, FAT32, exFAT, ext2/3/4 and limited Btrfs/XFS. Deleted-file recovery is partial; Btrfs/XFS deleted metadata hints cannot be exported.\n\nSearch by name, extension or category. TMP files are hidden from the view by default, not deleted.\n\nLarge lists show at most 750 rows per page; Ctrl+A selects the current page only. A warning indicates metadata concerns, not necessarily damaged content.\n\nPreview now shows scaled JPEG, PNG, BMP and GIF images and the first page of PDFs. Other PDF pages and animation frames are unchecked. DOCX may show a bounded text excerpt; Office page rendering is not included.\n\nIn Check file, Check contents complements the existing read check: image data is decoded, the first PDF page is rendered, and DOCX/XLSX/PPTX ZIP checksums and XML structures are checked. Readable structure does not confirm complete original contents. Links, macros and document actions are not executed.\n\nExtended preview and content checks read at most 32 MiB per file. Images are limited to 20 million pixels; XML, archive, time and memory limits may stop a check. A reached limit or Not checked does not prove damage. Protected documents are not decrypted. The source remains read-only; work from an image where possible.\n\nTo preview several files, select them together and open Preview. Previous and Next browse that selection; the position label shows the current file. Folders are omitted. The selection and source remain captured for this window even if the main view changes. Files without a preview show a notice and remain navigable. The corresponding direction is disabled at each end. Files never advance automatically. Switching cancels the previous processing and discards late results.\n\nFile signatures: In the “File signatures” tab, separate buttons search images, Office files, archives, audio or video. Supported candidates are JPEG, PNG, BMP, GIF, TIFF and WebP; DOCX/XLSX/PPTX and ODF packages; ZIP, 7z and TAR; WAV, MP3 with ID3v2 and Ogg/Opus; AVI and MP4. Legacy DOC/XLS/PPT and RAR are not supported yet. The regular image is searched read-only; partition offsets are ignored. Results are contiguous structural candidates without original names, folders or deletion status. They can be previewed, checked and exported, but this does not confirm complete original contents. Fragments are not reassembled. Size and candidate limits can make results incomplete. Resuming a saved export job searches the image again.',
   'Explore NTFS, FAT32, exFAT, ext2/3/4 y Btrfs/XFS con limitaciones. La recuperación de borrados es parcial; los indicios de Btrfs/XFS no se pueden exportar.\n\nBusque por nombre, extensión o categoría. Los TMP se ocultan en la vista, no se eliminan.\n\nSe muestran hasta 750 filas por página; Ctrl+A selecciona solo esa página. Una advertencia indica problemas de metadatos, no necesariamente del contenido.\n\nLa vista previa muestra imágenes JPEG, PNG, BMP y GIF reducidas y la primera página de los PDF. Las demás páginas y fotogramas no están comprobados. DOCX puede mostrar un extracto de texto limitado; no incluye representación de páginas Office.\n\nEn Comprobar archivo, Comprobar contenido complementa la lectura: decodifica imágenes, representa la primera página PDF y comprueba sumas ZIP y estructuras XML de DOCX/XLSX/PPTX. Una estructura legible no confirma contenidos originales completos. No se ejecutan enlaces, macros ni acciones.\n\nLa vista ampliada y comprobación leen hasta 32 MiB por archivo. Las imágenes se limitan a 20 millones de píxeles; los límites XML, de archivo, tiempo y memoria pueden detener la comprobación. Alcanzar un límite o quedar sin comprobar no demuestra daños. No se descifran documentos protegidos. La fuente sigue en solo lectura; trabaja con una imagen si es posible.\n\nPara varias vistas previas, selecciona los archivos juntos y abre Vista previa. Anterior y Siguiente recorren esa selección; el contador indica el archivo actual. Se omiten las carpetas. La ventana conserva selección y fuente aunque cambie la vista principal. Los archivos no representables muestran un aviso y permiten seguir. En cada extremo se desactiva la dirección correspondiente. No hay avance automático. Al cambiar se cancela el procesamiento anterior y se descartan resultados tardíos.\n\nFirmas de archivos: En la pestaña «Firmas de archivos», los botones buscan imágenes, archivos de Office, archivos comprimidos, audio o vídeo. Se reconocen JPEG, PNG, BMP, GIF, TIFF y WebP; paquetes DOCX/XLSX/PPTX y ODF; ZIP, 7z y TAR; WAV, MP3 con ID3v2 y Ogg/Opus; AVI y MP4. Aún no se admiten DOC/XLS/PPT clásicos ni RAR. Se examina la imagen normal en modo de solo lectura; se ignoran los desplazamientos de partición. Los resultados son candidatos estructurales contiguos sin nombres, carpetas ni estado de eliminación originales. Se pueden previsualizar, comprobar y exportar, pero esto no confirma que el contenido original esté completo. No se reconstruyen fragmentos. Los límites de tamaño y cantidad pueden dejar resultados incompletos. Al reanudar una exportación guardada, se vuelve a examinar la imagen.',
   '可浏览 NTFS、FAT32、exFAT、ext2/3/4 和有限支持的 Btrfs/XFS。已删除文件仅能部分恢复；Btrfs/XFS 的删除线索无法导出。\n\n可以按名称、扩展名和类别搜索。TMP 文件默认仅在界面中隐藏，并未删除。\n\n每页最多显示 750 行；Ctrl+A 仅选择当前页。警告表示元数据存在疑点，不一定代表内容损坏。\n\n预览现可显示缩小的 JPEG、PNG、BMP、GIF 图像以及 PDF 的第一页。其他 PDF 页面及动画帧未检查。DOCX 可显示有限的文本摘录，但不提供 Office 页面呈现。\n\n“检查文件”中的“检查内容”补充现有读取检查：解码图像、渲染 PDF 第一页，并检查 DOCX/XLSX/PPTX 的 ZIP 校验和及 XML 结构。结构可读不确认原始内容完整。不会执行链接、宏或文档操作。\n\n扩展预览及内容检查每个文件最多读取 32 MiB。图像限制为两千万像素；XML、归档、时间和内存限制可能终止检查。达到限制或未检查并不证明损坏。不会解密受保护文档。来源保持只读；建议使用镜像。\n\n同时选择多个文件并打开预览，可用“上一个”和“下一个”浏览此次选择，位置标签显示当前文件。文件夹会被忽略。即使主视图发生变化，此窗口仍保留原来的选择和来源。无法预览的文件会显示提示，仍可继续浏览。在首尾处相应方向不可用。不会自动切换文件。切换时会取消先前处理，并丢弃迟到的结果。\n\n文件签名：在“文件签名”选项卡中，可分别搜索图像、Office 文件、归档、音频或视频。支持 JPEG、PNG、BMP、GIF、TIFF、WebP；DOCX/XLSX/PPTX 与 ODF 包；ZIP、7z、TAR；WAV、带 ID3v2 的 MP3、Ogg/Opus；AVI、MP4。暂不支持旧式 DOC/XLS/PPT 和 RAR。程序以只读方式搜索整个普通映像，并忽略分区偏移。结果是连续的结构候选项，不含原始名称、文件夹或删除状态。可预览、检查和导出，但这不能确认原始内容完整。不会重组碎片。大小和数量限制可能导致结果不完整。继续已保存的导出任务时会重新搜索映像。',
   'Просмотр NTFS, FAT32, exFAT, ext2/3/4 и частично Btrfs/XFS. Восстановление удалённых файлов ограничено; подсказки Btrfs/XFS нельзя экспортировать.\n\nПоиск по имени, расширению и категории. TMP скрыты только в интерфейсе.\n\nДо 750 строк на странице; Ctrl+A выделяет лишь текущую страницу. Предупреждение относится к метаданным, а не обязательно к содержимому.\n\nПросмотр показывает уменьшенные JPEG, PNG, BMP и GIF, а также первую страницу PDF. Остальные страницы и кадры анимации не проверены. Для DOCX возможен ограниченный фрагмент текста; отображение страниц Office не предусмотрено.\n\nВ окне проверки файла действие «Проверить содержимое» дополняет чтение: декодирует изображения, отрисовывает первую страницу PDF и проверяет суммы ZIP и XML в DOCX/XLSX/PPTX. Читаемая структура не подтверждает полноту исходного содержимого. Ссылки, макросы и действия не выполняются.\n\nРасширенный просмотр и проверка читают до 32 МиБ на файл. Изображения ограничены 20 миллионами пикселей; лимиты XML, архива, времени и памяти могут остановить проверку. Достигнутый предел или отсутствие проверки не доказывает повреждение. Защищённые документы не расшифровываются. Источник остаётся только для чтения; по возможности работайте с образом.\n\nВыберите несколько файлов и откройте просмотр. Назад и Далее перемещают по этому выбору; счётчик показывает текущий файл. Папки пропускаются. Выбор и источник сохраняются для окна, даже если главная область изменится. Для недоступного просмотра показывается сообщение, но можно идти дальше. На концах соответствующее направление отключено. Автоматического перехода нет. При смене прежняя обработка отменяется, запоздалые результаты отбрасываются.\n\nСигнатуры файлов: На вкладке «Сигнатуры файлов» отдельные кнопки ищут изображения, файлы Office, архивы, аудио или видео. Поддерживаются JPEG, PNG, BMP, GIF, TIFF, WebP; пакеты DOCX/XLSX/PPTX и ODF; ZIP, 7z, TAR; WAV, MP3 с ID3v2, Ogg/Opus; AVI, MP4. Старые форматы DOC/XLS/PPT и RAR пока не поддерживаются. Обычный образ полностью проверяется только для чтения; смещение раздела игнорируется. Результаты — непрерывные структурные кандидаты без исходных имён, папок и сведений об удалении. Их можно просматривать, проверять и экспортировать, но это не подтверждает полноту оригинального содержимого. Фрагменты не собираются. Ограничения размера и количества могут сделать результаты неполными. При продолжении сохранённого экспорта образ проверяется заново.',
   'NTFS、FAT32、exFAT、ext2/3/4、制限付きの Btrfs/XFS を表示します。削除ファイルの復旧は限定的で、Btrfs/XFS の削除メタデータは書き出せません。\n\n名前、拡張子、カテゴリで検索できます。TMP は表示上隠すだけで削除しません。\n\n1ページ最大750行で、Ctrl+A は表示中のページのみ選択します。警告はメタデータの問題を示し、内容の損傷を確定しません。\n\nJPEG・PNG・BMP・GIF を縮小表示し、PDF の最初のページをプレビューできます。他の PDF ページやアニメーションフレームは未検査です。DOCX は制限付きのテキスト抜粋を表示できますが、Office のページ描画は含みません。\n\nファイル検査の「内容を検査」は従来の読み取り検査を補足します。画像を復号し、PDF の最初のページを描画し、DOCX/XLSX/PPTX の ZIP チェックサムと XML 構造を検査します。構造が読めても元の内容の完全性は確認できません。リンク、マクロ、文書アクションは実行しません。\n\n拡張プレビューと内容検査は1ファイル32 MiBまで読み取ります。画像は2千万ピクセルまでです。XML、アーカイブ、時間、メモリの上限で停止する場合があります。上限や未検査は破損を示しません。保護された文書は復号しません。ソースは読み取り専用で、可能ならイメージから作業してください。\n\n複数のファイルを選択してプレビューを開くと、「前へ」「次へ」で選択内を移動でき、位置表示で現在のファイルを確認できます。フォルダーは除外します。メイン画面を変更しても、このウィンドウの選択とソースは保持されます。表示できないファイルは案内を表示し、次へ移動できます。先頭と末尾では対応する方向を無効にします。自動切り替えはありません。切り替えると前の処理を中止し、遅れて届いた結果を破棄します。\n\nファイルシグネチャ：「ファイルシグネチャ」タブの各ボタンで、画像、Office、アーカイブ、音声、動画を検索します。JPEG、PNG、BMP、GIF、TIFF、WebP、DOCX/XLSX/PPTX・ODF パッケージ、ZIP・7z・TAR、WAV・ID3v2付きMP3・Ogg/Opus、AVI・MP4 に対応します。旧形式の DOC/XLS/PPT と RAR は未対応です。通常のイメージ全体を読み取り専用で検索し、パーティションオフセットは無視します。結果は連続した構造候補で、元の名前、フォルダー、削除状態は分かりません。プレビュー、検査、エクスポートはできますが、元の内容の完全性を確認するものではありません。断片は再構成しません。サイズと件数の上限により結果が不完全になる場合があります。保存済みエクスポートの再開時はイメージを再検索します。'
  )),
 'imaging': (
  ('Image erstellen', 'Create an image', 'Crear imagen', '创建镜像', 'Создание образа', 'イメージの作成'),
  (
   ("„Image erstellen / fortsetzen“ kopiert lesend von der Quelle in eine separate Image-Zieldatei. Beim Fortsetzen wird die bestehende Zieldatei weitergeschrieben. Statusdateien (.recovery.json/.journal) dienen zur sicheren Wiederaufnahme.\n\n"
    "Bei bestätigten Medienfehlern sind 0–3 zusätzliche Leseversuche möglich. Jeder Versuch kann ein defektes Laufwerk belasten. „Nullen + protokollieren“ erstellt Datenlücken; „Sicher anhalten“ stoppt am letzten gültigen Prüfpunkt.\n\n"
    "Zugriffsverweigerungen, Geräteabbrüche und unerwartet kurze Leseantworten sind keine bestätigten defekten Sektoren und führen zum Abbruch. Für mechanisch defekte Laufwerke professionelle schonende Verfahren bevorzugen.\n\n"
    "Das eigene Imaging-Fenster zeigt 100 Felder über die Quellbytes. Grün bedeutet lesbar gespeichert, Rot kennzeichnet protokollierten Nullersatz; schon ein kleiner Fehleranteil kann ein ganzes Feld rot markieren. Grün allein bestätigt keinen Vollvergleich. Nur das abschließende erfolgreiche Prüfergebnis meldet „bitgenau verifiziert“; eine unterbrochene Prüfung bleibt unbestätigt.\n\n"
    "„Schließen“ blendet die Ansicht aus, ohne den Auftrag anzuhalten. Über „Image erstellen / fortsetzen“ lässt sie sich wieder öffnen. „Unterbrechen“ hält kontrolliert an; „Einstellungen / fortsetzen“ führt zum bisherigen Auftrag. Image und Statusdateien zusammen behalten. Fehlerstellen-Bericht, Bericht speichern und Zielordner öffnen sind nach Abschluss oder Unterbrechung erreichbar. Die Dateisystemanalyse bleibt dagegen mit ihrem Zähler im Hauptfenster."),
   ("“Create / resume image” reads the source into a separate image file. Resume extends the existing destination; .recovery.json/.journal files hold checkpoints.\n\n"
    "For confirmed media errors, 0–3 retries are available. Each read can stress failing hardware. Zero fill records missing data; safe stop preserves the last valid checkpoint.\n\n"
    "Permission failures, disconnected devices and unexpected short reads stop the operation rather than being counted as bad sectors. Prefer specialist low-impact imaging for failing hardware.\n\n"
    "The imaging window has 100 cells across the source bytes. Green means read and saved; red marks recorded zero fill, even if only a small part of the cell had an error. Green alone does not confirm full comparison. Only a successful final check reports verification bit-for-bit; interrupted verification remains unconfirmed.\n\n"
    "Closing the view does not stop the job. Reopen it through “Create / resume image”. “Pause” interrupts safely; “Settings / resume” returns to the existing job. Keep the image and checkpoint files together. The bad-range report, save report and destination folder actions are available after completion or interruption. File-system scanning continues to show its counter in the main window."),
   ("«Crear / reanudar imagen» copia la fuente a otra imagen. Al reanudar continúa escribiendo en el archivo de destino; .recovery.json/.journal guardan el estado.\n\n"
    "Ante errores del medio confirmados hay 0–3 reintentos, que pueden dañarlo más. Rellenar con ceros deja datos ausentes; la parada segura conserva el último punto válido.\n\n"
    "Permisos denegados, desconexiones y lecturas cortas inesperadas detienen el proceso. Para discos dañados, prefiera herramientas especializadas.\n\n"
    "La ventana de imagen muestra 100 casillas sobre los bytes del origen. Verde significa leído y guardado; rojo señala ceros registrados, aunque el error afecte solo a una parte pequeña. Verde no confirma una comparación completa. Solo el resultado final correcto indica verificación bit a bit; una comprobación interrumpida queda sin confirmar.\n\n"
    "Cerrar la vista no detiene el trabajo. Ábrala desde «Crear / reanudar imagen». «Pausar» interrumpe de forma controlada y «Opciones / continuar» vuelve al trabajo existente. Conserve juntos imagen y archivos de estado. Tras terminar o interrumpir están disponibles el informe de errores, guardar informe y abrir destino. El análisis del sistema de archivos mantiene su contador en la ventana principal."),
   ("“创建／继续镜像”只读访问源并写入单独的目标镜像。续传时继续写入现有文件；.recovery.json/.journal 用于恢复。\n\n"
    "确认的介质错误可重试 0–3 次，但每次读取都可能加重损坏。填零会留下数据缺口；安全停止会保留最后有效检查点。\n\n"
    "拒绝访问、设备断开和异常短读会终止操作，不会当作坏扇区。故障硬盘建议使用专业低负载工具。\n\n"
    "镜像窗口用 100 个格子表示来源字节范围。绿色表示已读取并保存；红色表示已记录的零填充，即使错误只影响该格的一小部分。绿色本身不代表完整比较通过。只有最终成功的校验结果才能确认逐位一致；中断的校验仍未确认。\n\n"
    "关闭视图不会停止任务，可通过“创建 / 继续镜像”重新打开。“暂停”有序中断，“设置 / 继续”返回原任务。请将镜像和检查点文件一起保留。完成或中断后可查看错误位置报告、保存报告及打开目标文件夹。文件系统扫描仍在主窗口显示计数器。"),
   ("«Создать / продолжить образ» читает источник и записывает отдельный файл образа. При возобновлении файл дописывается; .recovery.json/.journal хранят контрольные точки.\n\n"
    "Для подтверждённых ошибок носителя предусмотрено 0–3 повтора. Они могут ухудшить состояние диска. Нулевое заполнение означает потерю данных; безопасная остановка сохраняет контрольную точку.\n\n"
    "Отказ в доступе, отключение и короткие ответы вызывают остановку. При аппаратных повреждениях применяйте специализированные средства.\n\n"
    "Окно создания образа показывает 100 ячеек по байтам источника. Зелёный означает прочитанное и сохранённое, красный — записанное заполнение нулями, даже при малой доле ошибки. Зелёный сам по себе не подтверждает полного сравнения. Только успешная итоговая проверка означает побитовое совпадение; прерванная проверка остаётся неподтверждённой.\n\n"
    "Закрытие окна не останавливает работу; откройте её через создание/продолжение образа. «Приостановить» останавливает контролируемо, «Настройки / продолжить» возвращает к заданию. Храните образ вместе с файлами контрольных точек. После завершения или остановки доступны отчёт о сбойных участках, сохранение отчёта и папка назначения. Счётчик анализа файловой системы остаётся в главном окне."),
   ("「イメージ作成／再開」は元ディスクを読み、別のイメージファイルへ書き込みます。再開時は既存ファイルへ追記し、.recovery.json/.journal に状態を保存します。\n\n"
    "確定した媒体エラーのみ0～3回の再試行が可能ですが、故障を悪化させる恐れがあります。ゼロ埋めは欠損を残し、安全停止は有効なチェックポイントを保持します。\n\n"
    "アクセス拒否、切断、短い読み取りは停止します。故障媒体には専門的な手法を推奨します。\n\n"
    "イメージ作成ウィンドウはソースのバイト範囲を100マスで表示します。緑は読み取り・保存済み、赤は記録されたゼロ埋めで、影響がごく一部でもマス全体が赤くなることがあります。緑だけでは完全比較の合格を示しません。最終検証の成功だけがビット単位の一致を確認し、中断した検証は未確認です。\n\n"
    "表示を閉じても処理は止まらず、イメージ作成・再開から再表示できます。「一時停止」は制御された中断を行い、「設定／再開」で元の処理に戻ります。イメージとチェックポイントファイルを一緒に保持してください。完了・中断後にエラー位置レポート、レポート保存、保存先フォルダーを利用できます。ファイルシステム解析のカウンターは引き続きメインウィンドウに表示します。"),
  )),
 'export': (
  ('Stapel-Export', 'Batch export', 'Exportación por lotes', '批量导出', 'Пакетный экспорт', '一括エクスポート'),
  (
   ('Wähle Dateien oder Ordner und nutze „Export prüfen“. Die Vorprüfung bewertet Metadaten, nicht den vollständigen Inhalt. „Bereit“ garantiert keine intakte Datei; bestätigte Zuordnungskonflikte werden gesperrt. „Stapel-Export / fortsetzen“ speichert in einem eigenen Exportordner auf dem gewählten Ziel. Verwende einen anderen physischen Datenträger. Fremde vorhandene Dateien werden nicht überschrieben; verborgene TMP-Dateien können bei Ordnerexporten enthalten sein.\n\nDas separate Fortschrittsfenster öffnet automatisch. „Schließen“ blendet nur diese Ansicht aus. Über „Fortschritt / Ergebnis“ lässt sie sich wieder öffnen; der Auftrag läuft weiter oder bleibt pausiert.\n\n„Pause“ hält den laufenden Auftrag an der nächsten Lese-/Schreibgrenze an. Bis dahin erscheint eine Pause-Anforderung. Nach Bestätigung bleiben angefangene Datei, Zähler und SHA256-Berechnung erhalten. „Fortsetzen“ arbeitet im selben Auftrag weiter, solange Tenshi geöffnet bleibt.\n\n„Abbrechen“ beendet kontrolliert und entfernt eine unvollständige Datei. Erst nach abgeschlossenem Abbruch wird „Fortsetzen“ wieder aktiv. Es übernimmt die ursprüngliche Quelle, Auswahl und den Zielordner, auch wenn die Dateiansicht inzwischen etwas anderes zeigt. Fertige Dateien werden erneut geprüft; unvollständige Dateien beginnen von vorn. Bereits vollständig kopierte Dateien mit gespeichertem Prüfwert können eine unterbrochene Zielprüfung fortsetzen. Eine geänderte Quelle oder ein fehlender bisheriger Exportordner wird beim direkten Fortsetzen gemeldet.\n\nNach Neustart: „Exportauftrag öffnen“ → erzeugten Tenshi_Export_…-Unterordner wählen. Beim manuellen Fortsetzen über „Stapel-Export“: gleiche Quelle und Auswahl, ursprünglicher Zielordner.\n\nJedes der 100 Rasterfelder steht für ein Prozent aller geplanten Dateigrößen; bei reinen Ordner-/Null-Byte-Plänen gilt die Eintragszahl. Blau bedeutet kopiert, noch ungeprüft; Grün bedeutet Export bestätigt. Rot kennzeichnet Exportfehler, unbestätigte Anteile bleiben erkennbar. Dateigrenzen können mitten in einem Feld liegen: Bereits bestätigte Bytes der vorherigen und ungeprüfte Bytes der laufenden Datei bleiben bis zu deren Bestätigung gemischt. Die Felder sind keine Datenträgersektoren.\n\nSHA256-Berechnung und Zielprüfung erscheinen als Textphase. Nach jeder vollständig kopierten und bestätigten Datei entsteht eine .sha256 unter Pruefsummen_Einzeln. Erst nach vollständig erfolgreichem Export wird SHA256SUMS.sha256 sicher gespeichert und rückgelesen; danach werden die unveränderten eigenen Einzeldateien und der leere Zwischenordner entfernt. Bei Abbruch oder Fehlern bleiben bisherige Einzeldateien erhalten. Weitere fremde Dateien erhalten den Ordner; geänderte Prüfsummendateien werden nicht überschrieben oder entfernt. Relative Prüfsummenpfade gelten ab dem Exportordner.\n\n„Ergebnisbericht“ zeigt Einzelstatus, bestätigte bzw. noch unbestätigte SHA256-Werte und den Prüfumfang. „Bericht speichern“ beginnt im zugehörigen Exportordner und schlägt einen neuen Namen vor. „Zielordner öffnen“ führt zum Exportordner. Ein bestätigter Export beweist nicht, dass die ursprünglichen Dateiinhalte vollständig oder unbeschädigt waren.\n\nVor dem ersten Schreibzugriff zeigt die Zielprüfung die geplanten Dateiinhalte, eine Obergrenze zusätzlich benötigter Dateibytes und den aktuell verfügbaren Platz. Vollständige Dateien des bisherigen Auftrags werden zur erneuten Prüfung berücksichtigt, nicht erneut als Kopierbedarf gezählt. Die Schätzung enthält keinen zusätzlichen Platz für Dateisystem-Metadaten, Berichte und Prüfsummen. Bei Platzmangel ist die Warnung mit Nein vorausgewählt; ein ausdrücklich bestätigter Start bleibt möglich. Dateien oberhalb der erkannten FAT/FAT32-Grenze von 4 GiB minus 1 Byte erfordern ein anderes Ziel. Bei unbekannten VM-/Netzwerk-Dateisystemen lässt sich diese Grenze nicht zuverlässig vorhersagen. Ablehnen legt keinen Exportordner an; eine abgelehnte Wiederaufnahme bleibt fortsetzbar.\n\nDas Fortschrittsfenster bleibt über dem Hauptfenster und wird beim Öffnen daran zentriert. Ein erneuter Klick auf Stapel-Export zeigt den laufenden oder pausierten Auftrag wieder an, ohne eine neue Auswahl, einen neuen Zielordner oder einen zweiten Export zu starten.\n\nNach einem Programmneustart öffnet „Exportauftrag öffnen“ den bisherigen erzeugten Export-Unterordner. Neue Aufträge enthalten die ursprüngliche Auswahl und Scan-Einstellungen in ihrer Statusdatei. Vor Zugriff auf die gespeicherte Quelle ist eine Bestätigung erforderlich. Das Dateisystem wird schreibgeschützt erneut eingelesen; Quelle und vollständiger Plan müssen übereinstimmen. Der Textzähler zeigt die Vorbereitung. Abbrechen oder Nein verändert dabei den Exportordner nicht. Fertige Dateien werden weiter per SHA256 geprüft; unvollständige Dateien beginnen von vorn. Ältere Aufträge ohne Auswahl weiter manuell mit derselben Quelle, Auswahl und dem ursprünglichen Zielordner fortsetzen. Es wird kein Index-/Inhaltscache und keine Auftragsliste im Benutzerprofil gespeichert. Die ursprüngliche Quelle muss erreichbar und unverändert sein; vorhandene unbekannte Dateien werden nicht überschrieben.\n\nIm Ergebnisbericht öffnet „Exportierte Datei prüfen …“ die Inhaltsprüfung für eine bereits exportierte Datei. Die Auswahl beginnt im Unterordner files. Dabei werden nur die Zieldatei gelesen und weder Quelle noch Bericht oder Prüfsummen verändert. So kann die Prüfung auf dem Zielmedium erfolgen, ohne das Quellmedium erneut zu lesen.'),
   ('Select files or folders and run “Check export”. Preflight checks metadata, not full contents. “Ready” does not guarantee intact files; confirmed mapping conflicts are blocked. Batch export writes into its own folder at the selected destination. Use a different physical disk. Unrelated existing files are not overwritten; recursive folder exports may include hidden TMP files.\n\nThe separate progress window opens automatically. Closing it hides the view only. Reopen it through “Progress / result”; the job continues running or remains paused.\n\n“Pause” requests a stop at the next read/write boundary. Until acknowledged, the window shows a pause request. Once paused, the partial file, counters and SHA256 calculation are retained. “Resume” continues the same worker while Tenshi stays open.\n\n“Cancel” stops the job cleanly and removes an incomplete file. Once cancellation finishes, “Resume” becomes available again. It uses the original source, selection and destination even if the file browser now shows something else. Completed files are verified again; incomplete files restart from the beginning. A fully copied file with a saved digest can finish an interrupted destination check. Direct resume reports a changed source or missing original export folder.\n\nAfter restart: “Open export job” → choose the generated Tenshi_Export_… subfolder. For manual resume via “Batch export”: same source and selection, original destination folder.\n\nEach of the 100 cells represents one percent of the total planned file sizes; folder-only/zero-byte plans use entry count. Blue means copied but not yet verified; green means export verified. Red marks export errors; unverified portions remain distinct. A file boundary may split a cell: verified bytes of the previous file and unverified bytes of the current file remain mixed until that file is verified. These are not disk sectors.\n\nSHA256 calculation and destination checking appear as text phases. Each fully copied and verified file gets a .sha256 under Pruefsummen_Einzeln. Only a fully successful export saves and reads back SHA256SUMS.sha256; afterwards unchanged individual checksum files owned by the job and their empty folder are removed. Cancellation or errors retain existing individual files. Unrelated files keep the folder in place; modified checksum files are not overwritten or deleted. Checksum paths are relative to the export folder.\n\n“Results report” shows individual status, verified or still unverified SHA256 values and the verification scope. “Save report” starts in the export folder and suggests a new name. “Open destination folder” opens the export folder. A verified export does not prove that the original file contents were complete or undamaged.\n\nBefore the first write, the destination check shows planned file contents, an upper estimate of additional file bytes and currently available space. Complete existing files from the saved job are counted for rechecking rather than copying again. Filesystem metadata, reports and checksums need additional space. A low-space warning defaults to No; an explicitly confirmed start is still possible. Files exceeding a detected FAT/FAT32 limit of 4 GiB minus 1 byte require another destination. Limits behind unknown VM/network filesystems cannot be reliably predicted. Declining creates no export folder; a declined resume remains resumable.\n\nThe progress window stays above the main window and is centered on it when opened. Clicking Batch export again reopens the running or paused job without a new selection, destination or second export.\n\nAfter restarting Tenshi, Open export job opens the previously generated export subfolder. New jobs store the original selection and scan settings in their status file. Confirmation is required before accessing the saved source. The filesystem is scanned again in read-only mode; source and complete plan must match. A text counter shows preparation. Cancel or No during preparation leaves the export folder unchanged. Complete files still undergo SHA256 checking; incomplete files restart from the beginning. Older jobs without saved selections retain manual resume using the same source, selection and original destination folder. No index/content cache or job list is stored in the user profile. The original source must remain accessible and unchanged; unknown existing files are not overwritten.\n\nIn the result report, Check exported file opens content checking for an exported file. Selection starts in the files subfolder. Only the target file is read; the source, report and checksums are unchanged. This lets you check the target without reading the source medium again.'),
   ('Seleccione archivos o carpetas y use «Comprobar exportación». La comprobación previa evalúa metadatos, no todo el contenido. «Listo» no garantiza archivos íntegros; los conflictos de asignación confirmados se bloquean. La exportación por lotes crea su propia carpeta en el destino elegido. Use otro disco físico. No se sobrescriben archivos ajenos; la exportación de carpetas puede incluir TMP ocultos.\n\nLa ventana de progreso se abre automáticamente. Cerrarla solo oculta la vista. Puede volver a abrirla mediante «Progreso / resultado»; el trabajo continúa o permanece en pausa.\n\n«Pausar» solicita una pausa en el siguiente límite de lectura o escritura. Mientras se espera, se indica la solicitud. Al confirmarse, se conservan el archivo parcial, los contadores y el cálculo SHA256. «Continuar» sigue con el mismo proceso mientras Tenshi esté abierto.\n\n«Cancelar» detiene el trabajo de forma controlada y elimina el archivo incompleto. Al terminar la cancelación se activa «Continuar». Se reutilizan origen, selección y destino originales, aunque el explorador muestre otra cosa. Los archivos completos se verifican de nuevo; los incompletos se copian desde el principio. Una copia completa con suma guardada puede terminar una verificación de destino interrumpida. La continuación directa avisa si cambió el origen o falta la carpeta de exportación original.\n\nTras reiniciar: «Abrir trabajo de exportación» → elegir la subcarpeta Tenshi_Export_… generada. Para reanudar manualmente mediante «Exportación por lotes»: misma fuente y selección, carpeta de destino original.\n\nCada una de las 100 casillas representa el uno por ciento del tamaño total previsto; los planes solo de carpetas o de cero bytes usan el número de entradas. Azul: copiado sin verificar; verde: exportación confirmada; rojo: error. Los datos sin confirmar se distinguen. Un límite entre archivos puede dividir una casilla: combina datos confirmados del archivo anterior y pendientes del actual hasta su verificación. No representa sectores físicos.\n\nEl cálculo SHA256 y la verificación del destino se muestran como fases de texto. Cada archivo completo y confirmado recibe un .sha256 en Pruefsummen_Einzeln. Solo una exportación totalmente correcta guarda y vuelve a leer SHA256SUMS.sha256; después elimina sus archivos individuales sin cambios y la carpeta vacía. Al cancelar o fallar se conservan las sumas existentes. Los archivos ajenos mantienen la carpeta; las sumas modificadas no se sobrescriben ni eliminan. Las rutas de las sumas son relativas a la carpeta de exportación.\n\n«Informe de resultados» muestra estados, valores SHA256 confirmados o pendientes y el alcance de la comprobación. «Guardar informe» propone un nombre nuevo en la carpeta de exportación. «Abrir carpeta de destino» abre esa carpeta. Confirmar la exportación no demuestra que el contenido original estuviera completo o intacto.\n\nAntes de escribir, la comprobación del destino muestra el contenido previsto, una estimación superior de bytes adicionales y el espacio disponible. Los archivos completos del trabajo guardado se cuentan para su comprobación, no para volver a copiarlos. Metadatos, informes y sumas necesitan espacio adicional. La advertencia de espacio insuficiente selecciona No; se puede iniciar con confirmación explícita. Los archivos que superan el límite FAT/FAT32 detectado de 4 GiB menos 1 byte requieren otro destino. No se pueden predecir con fiabilidad los límites de sistemas desconocidos de máquinas virtuales o de red. Rechazar no crea la carpeta de exportación; una reanudación rechazada puede volver a intentarse.\n\nLa ventana de progreso permanece sobre la principal y se centra en ella al abrirse. Pulsar de nuevo Exportación por lotes muestra el trabajo en curso o pausado sin otra selección, destino ni una segunda exportación.\n\nTras reiniciar Tenshi, Abrir trabajo de exportación abre la subcarpeta de exportación generada anteriormente. Los nuevos trabajos guardan la selección y los ajustes de análisis en su archivo de estado. Se requiere confirmación antes de acceder a la fuente guardada. El sistema de archivos se vuelve a leer en modo de solo lectura; la fuente y el plan completo deben coincidir. Un contador de texto muestra la preparación. Cancelar o No durante la preparación no modifica la carpeta. Los archivos completos se comprueban con SHA256; los incompletos empiezan de nuevo. Los trabajos antiguos sin selección guardada conservan la reanudación manual con la misma fuente, selección y destino original. No se guarda caché de índices/contenido ni lista de trabajos en el perfil. La fuente original debe seguir accesible y sin cambios; no se sobrescriben archivos desconocidos.\n\nEn el informe, Comprobar archivo exportado comprueba el contenido de un archivo ya exportado. La selección empieza en files. Solo se lee el archivo de destino; no cambia la fuente, informe ni sumas. Permite comprobar el destino sin volver a leer el medio original.'),
   ('选中文件或文件夹并运行“检查导出”。预检查评估元数据，不验证全部内容；“就绪”不保证文件完好，已确认的分配冲突会被阻止。批量导出会在所选目标中建立独立文件夹。请使用另一块物理磁盘。不覆盖无关的现有文件；递归导出文件夹可能包含隐藏的 TMP 文件。\n\n独立的进度窗口会自动打开。关闭它仅隐藏视图；通过“进度 / 结果”可以重新打开，任务会继续运行或保持暂停。\n\n“暂停”会请求在下一个读写边界暂停；等待期间会显示暂停请求。确认暂停后，未完成文件、计数器和 SHA256 计算状态都会保留。在 Tenshi 保持打开时，“继续”会让同一任务接着运行。\n\n“取消”会有序停止任务并删除未完成的文件。取消结束后，“继续”按钮重新可用。即使文件浏览器已经显示其他内容，也会使用原来的来源、选择和目标文件夹。已完成文件会重新校验；未完成文件将从头复制。完整复制且已保存校验值的文件可以完成先前中断的目标校验。直接继续时，如果原来源改变或原导出文件夹缺失，会报告错误。\n\n重启后：“打开导出任务” → 选择生成的 Tenshi_Export_… 子文件夹。通过“批量导出”手动继续时：使用相同来源和文件选择，并选择原始目标文件夹。\n\n100 个格子各表示计划文件总大小的百分之一；仅含文件夹或零字节的计划按条目数显示。蓝色表示已复制但未校验，绿色表示导出已确认，红色表示导出错误；未确认部分单独标识。文件边界可能位于格子内部：前一文件已确认的字节与当前文件未校验的字节会保持混合状态，直到当前文件校验完成。格子不代表磁盘扇区。\n\nSHA256 计算与目标校验以文字阶段显示。每个完整复制且确认的文件都会在 Pruefsummen_Einzeln 中生成 .sha256。只有全部导出成功后，才安全保存并回读 SHA256SUMS.sha256；随后删除任务自身未被修改的单独校验文件和空的中间文件夹。取消或出错时保留已有的单独文件。含其他文件的文件夹会保留；已修改的校验文件不会被覆盖或删除。校验列表中的路径以导出文件夹为基准。\n\n“结果报告”包含每个条目的状态、已确认或未确认的 SHA256 值及校验范围。“保存报告”从对应导出文件夹开始并建议新名称。“打开目标文件夹”打开该文件夹。导出已确认并不证明原始文件内容完整无损。\n\n首次写入前，目标检查会显示计划文件内容大小、额外所需字节的估算上限及当前可用空间。已保存任务中的完整文件将重新检查，不计为需要重新复制的数据。文件系统元数据、报告和校验文件还需额外空间。空间不足警告默认选择“否”，仍可明确确认后开始。超过已识别 FAT/FAT32 的 4 GiB 减 1 字节限制的文件需更换目标。未知虚拟机或网络文件系统背后的限制无法可靠预测。拒绝不会创建导出文件夹；拒绝继续的任务之后仍可继续。\n\n进度窗口保持在主窗口上方，打开时相对主窗口居中。再次点击批量导出可重新显示正在进行或暂停的任务，不会重新选择文件或目标，也不会启动第二次导出。\n\n重启 Tenshi 后，通过“打开导出任务”选择原先生成的导出子文件夹。新任务会在状态文件中保存原始选择和扫描设置。访问保存的来源前需要确认。将以只读方式重新扫描文件系统，来源和完整计划必须匹配。文字计数器显示准备进度。准备时取消或选择“否”不会更改导出文件夹。完整文件仍会进行 SHA256 检查，不完整文件从头复制。没有保存选择的旧任务仍可手动使用相同来源、选择和原始目标文件夹继续。不会在用户配置目录保存索引／内容缓存或任务列表。原始来源必须保持可访问且未更改，未知的已有文件不会被覆盖。\n\n在结果报告中，“检查导出的文件”可检查已导出文件的内容。选择从 files 子文件夹开始。仅读取目标文件，不更改来源、报告或校验和，因此无需再次读取原始介质。'),
   ('Выберите файлы или папки и выполните предварительную проверку экспорта. Она оценивает метаданные, а не всё содержимое. «Готово» не гарантирует целостность; подтверждённые конфликты размещения блокируются. Пакетный экспорт создаёт отдельную папку в выбранном назначении. Используйте другой физический диск. Посторонние существующие файлы не перезаписываются; экспорт папок может включать скрытые TMP.\n\nОкно прогресса открывается автоматически. Закрытие скрывает только представление. Откройте его снова через «Прогресс / результат»: работа продолжается или остаётся на паузе.\n\n«Пауза» запрашивает остановку на ближайшей границе чтения или записи; до подтверждения показывается запрос. Затем сохраняются частичный файл, счётчики и состояние SHA256. «Продолжить» возобновляет тот же процесс, пока Tenshi открыт.\n\n«Отмена» контролируемо завершает работу и удаляет неполный файл. После завершения отмены снова доступно «Продолжить». Используются прежние источник, выбор и папка назначения, даже если файловый список уже показывает другое. Готовые файлы проверяются повторно, неполные копируются с начала. Полная копия с сохранённой суммой может завершить прерванную проверку назначения. При прямом продолжении сообщается об изменении источника или отсутствии прежней папки экспорта.\n\nПосле перезапуска: «Открыть задание экспорта» → созданная подпапка Tenshi_Export_…. Для ручного продолжения через пакетный экспорт: прежний источник и выбор, исходная папка назначения.\n\nКаждая из 100 ячеек означает один процент общего запланированного размера; для папок и нулевых файлов используется число элементов. Синий означает скопированные, ещё не проверенные данные, зелёный — подтверждённый экспорт, красный — ошибку. Неподтверждённые части различаются отдельно. Граница файла может проходить внутри ячейки: подтверждённые байты предыдущего файла и непроверенные текущего остаются смешанными до проверки текущего файла. Это не секторы диска.\n\nРасчёт SHA256 и проверка назначения показываются текстовыми этапами. Каждый полностью скопированный и подтверждённый файл получает .sha256 в Pruefsummen_Einzeln. Только полностью успешный экспорт сохраняет и перечитывает SHA256SUMS.sha256, после чего удаляет неизменённые собственные отдельные суммы и пустую промежуточную папку. При отмене и ошибках прежние суммы сохраняются. Посторонние файлы сохраняют папку; изменённые суммы не перезаписываются и не удаляются. Пути считаются относительно папки экспорта.\n\n«Отчёт о результатах» показывает статусы, подтверждённые или ещё не подтверждённые SHA256 и объём проверки. Сохранение отчёта начинается в папке экспорта и предлагает новое имя. Кнопка папки открывает её. Подтверждённый экспорт не доказывает целостность исходного содержимого.\n\nПеред первой записью проверка назначения показывает планируемый объём, верхнюю оценку дополнительных байтов и свободное место. Полные файлы сохранённого задания учитываются для повторной проверки, а не для нового копирования. Метаданные, отчёты и контрольные суммы требуют дополнительного места. При нехватке места по умолчанию выбрано Нет; запуск возможен после явного подтверждения. Файлы сверх обнаруженного предела FAT/FAT32 в 4 ГиБ минус 1 байт требуют другого назначения. Ограничения неизвестных файловых систем общих папок виртуальных машин и сети нельзя надёжно предсказать. Отказ не создаёт папку экспорта; отклонённое продолжение можно повторить.\n\nОкно прогресса остаётся над главным окном и центрируется относительно него при открытии. Повторное нажатие пакетного экспорта показывает выполняемое или приостановленное задание без нового выбора, назначения или второго экспорта.\n\nПосле перезапуска Tenshi действие «Открыть задание экспорта» открывает прежнюю созданную подпапку экспорта. Новые задания сохраняют исходный выбор и настройки сканирования в файле состояния. Перед доступом к сохранённому источнику требуется подтверждение. Файловая система снова читается только для чтения; источник и полный план должны совпадать. Текстовый счётчик показывает подготовку. Отмена или Нет во время подготовки не изменяет папку. Полные файлы проверяются по SHA256, неполные копируются заново. Старые задания без сохранённого выбора можно продолжать вручную с тем же источником, выбором и исходной папкой назначения. Кэш индекса/содержимого и список заданий в профиле не сохраняются. Исходный источник должен оставаться доступным и неизменным; неизвестные существующие файлы не перезаписываются.\n\nВ отчёте действие «Проверить экспортированный файл» проверяет содержимое уже сохранённого файла. Выбор начинается в подпапке files. Читается только файл назначения; источник, отчёт и суммы не изменяются. Исходный носитель повторно читать не требуется.'),
   ('ファイルやフォルダーを選び、エクスポートの事前検査を実行します。検査対象はメタデータで、全内容ではありません。「準備完了」は完全性を保証せず、確認された割り当て競合はブロックします。一括エクスポートは選択先に専用フォルダーを作成します。別の物理ディスクを使用してください。無関係な既存ファイルは上書きしません。フォルダーの再帰的な出力には非表示の TMP が含まれる場合があります。\n\n独立した進捗ウィンドウが自動で開きます。閉じても表示を隠すだけです。「進捗 / 結果」から再表示でき、処理は継続するか、一時停止のままになります。\n\n「一時停止」は次の読み書きの区切りで停止を要求します。確認までは要求中と表示します。停止後は途中のファイル、カウンター、SHA256 の計算状態を保持します。Tenshiを開いている間、「再開」は同じ処理を続けます。\n\n「中止」は制御された終了を行い、未完了のファイルを削除します。中止完了後は「再開」が再び有効になります。ファイル画面が別の内容を表示していても、元のソース、選択、保存先を使います。完了済みのファイルは再検証し、未完了のファイルは最初からコピーします。完全にコピーされチェック値が保存されたファイルは、中断された出力先検証を完了できます。直接再開する際、元のソースが変わった場合や元の出力フォルダーがない場合はエラーを表示します。\n\n再起動後：「出力処理を開く」→ 生成された Tenshi_Export_… サブフォルダーを選択。一括エクスポートから手動で再開する場合は、同じソースと選択、および元の保存先フォルダーを指定します。\n\n100マスは計画されたファイルサイズの合計を1%ずつ表します。フォルダーのみ・ゼロバイトの計画では項目数を使います。青はコピー済み・未検証、緑は出力確認済み、赤は出力エラーです。未確認部分も区別します。ファイル境界がマスの途中にあると、前のファイルの確認済み部分と現在のファイルの未検証部分が混在し、現在の検証完了までその表示が続きます。物理セクターの表示ではありません。\n\nSHA256 の計算と出力先検証は文字で表示します。完全にコピーされ確認済みの各ファイルについて、Pruefsummen_Einzeln に .sha256 を保存します。全出力の成功後に SHA256SUMS.sha256 を安全に保存して読み戻し、変更されていない自身の個別チェックサムと空の中間フォルダーを削除します。中止やエラー時は既存の個別ファイルを保持します。別のファイルがあればフォルダーは残し、変更されたチェックサムは上書きも削除もしません。パスの基準は出力フォルダーです。\n\n結果レポートには項目ごとの状態、確認済み・未確認の SHA256 値、検証範囲を表示します。レポート保存は出力フォルダーから始まり、新しい名前を提案します。保存先ボタンでそのフォルダーを開けます。出力の確認は、元のファイル内容が完全・無傷だったことを保証しません。\n\n最初の書き込み前に、保存先の検査で予定内容量、追加ファイル容量の上限見積もり、現在の空き容量を表示します。保存済みの完全なファイルは再検査の対象となり、再コピー容量には含めません。メタデータ、レポート、チェックサムには追加容量が必要です。容量不足の警告は「いいえ」が既定ですが、明示的に確認すれば開始できます。検出した FAT/FAT32 の上限（4 GiB − 1 バイト）を超えるファイルには別の保存先が必要です。不明な仮想マシンやネットワーク共有の制限は確実には予測できません。拒否しても出力フォルダーは作られず、再開を拒否した処理も後で再開できます。\n\n進捗ウィンドウはメインウィンドウの上に表示され、開くときにその中央へ配置されます。一括エクスポートを再度クリックすると、実行中または一時停止中の処理を再表示します。選択や保存先の指定をやり直したり、別の出力処理を開始したりはしません。\n\nTenshi の再起動後は「出力処理を開く」で以前に生成された出力サブフォルダーを選びます。新しい処理は元の選択と解析設定を状態ファイルに保存します。保存されたソースへのアクセス前に確認が必要です。ファイルシステムを読み取り専用で再解析し、ソースと計画全体の一致を検査します。準備中は文字のカウンターを表示し、中止や「いいえ」で出力フォルダーを変更しません。完全なファイルは引き続き SHA256 で検査し、不完全なファイルは最初からコピーします。選択情報のない古い処理は同じソース、選択、元の保存先を手動で指定して再開できます。ユーザープロファイルに索引・内容キャッシュや処理一覧は保存しません。元のソースが参照可能で変更されていない必要があり、不明な既存ファイルは上書きしません。\n\n結果レポートの「出力したファイルを検査」で、保存済みファイルの内容を検査できます。選択は files サブフォルダーから始まります。出力先ファイルのみを読み取り、ソース、レポート、チェックサムは変更しません。元の媒体を再読せずに検査できます。'),
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
   ("Mit „Fehlerprotokoll“ (oben rechts) öffnest du die technischen Meldungen. Die Datei liegt unter Windows normalerweise in %LOCALAPPDATA%\\Tenshi\\Logs. Veröffentliche Protokolle erst nach Prüfung auf private Pfade.\n\n"
    "Bei Build-Problemen prüfe tenshi-build.log und führe check_windows.bat aus. run_tests.bat startet die Tests separat; dabei absichtlich erzeugte Fehler können protokolliert werden.\n\n"
    "Für die EXE wird 64-Bit-Python ab 3.11 und PyInstaller benötigt. Der Quellcode enthält kein fertig gebautes Windows-Programm. Treten echte Laufwerksfehler auf, greife nicht wiederholt auf ein verdächtig beschädigtes Medium zu.\n\n"
    "Exportfehler unterscheiden verweigerten Zugriff, schreibgeschützte Ziele, fehlenden Speicherplatz und nicht unterstützte Dateioperationen. „Invalid argument“ beweist keine fehlenden Schreibrechte; gemeinsam genutzte VM-Ordner können eingeschränkt sein. Die Originaldiagnose bleibt sichtbar. Bei Flatpak muss der gewählte Zielordner zugänglich sein. Tenshi erweitert keine Geräte- oder Ordnerrechte. Fehler zusätzlicher Prüfsummendateien stehen gesondert im Bericht; eine gespeicherte Sammeldatei bleibt bei blockierter Bereinigung erhalten."),
   ("Open “Error log” (top right) to inspect technical records, normally stored under %LOCALAPPDATA%\\Tenshi\\Logs on Windows. Review logs for private paths before sharing.\n\n"
    "For build failures check tenshi-build.log and run check_windows.bat. run_tests.bat runs tests separately; intentionally simulated failures may be logged.\n\n"
    "A Windows EXE requires 64-bit Python 3.11+ and PyInstaller. Source packages do not contain prebuilt binaries. Do not keep retrying reads on suspected failing media.\n\n"
    "Export errors distinguish denied access, read-only destinations, lack of free space and unsupported file operations. “Invalid argument” does not prove missing write permission; VM shared folders may restrict operations. Original diagnostics remain visible. Flatpak needs access to the selected destination. Tenshi does not grant device or folder permissions. Additional checksum-file errors are reported separately; a saved summary is retained if cleanup is blocked."),
   ("Abra «Registro de errores» para ver los mensajes técnicos en %LOCALAPPDATA%\\Tenshi\\Logs. Revise si hay rutas privadas antes de compartir.\n\n"
    "Para errores de compilación consulte tenshi-build.log y check_windows.bat. run_tests.bat ejecuta los tests por separado; algunos simulan errores.\n\n"
    "La EXE requiere Python de 64 bits 3.11+ y PyInstaller. El código fuente no incluye una EXE compilada. Evite nuevas lecturas en discos defectuosos.\n\n"
    "Los errores distinguen acceso denegado, destinos de solo lectura, falta de espacio y operaciones no compatibles. «Invalid argument» no demuestra falta de permisos; las carpetas compartidas de una VM pueden limitar operaciones. Se conserva el diagnóstico original. Flatpak necesita acceso al destino; Tenshi no concede permisos. Los errores de archivos de sumas se muestran aparte; un resumen guardado se conserva si la limpieza está bloqueada."),
   ("点击右上角“错误日志”查看技术记录，Windows 中通常位于 %LOCALAPPDATA%\\Tenshi\\Logs。分享前请检查私人路径。\n\n"
    "构建失败请查看 tenshi-build.log 并运行 check_windows.bat。run_tests.bat 单独执行测试；部分测试会模拟错误。\n\n"
    "构建 EXE 需要 64 位 Python 3.11+ 和 PyInstaller。源码包不包含预编译程序。疑似硬件故障时避免反复读取。\n\n"
    "导出错误区分访问被拒绝、只读目标、空间不足与不支持的操作。“Invalid argument”不能证明缺少写入权限；虚拟机共享文件夹可能限制操作。原始诊断会保留。Flatpak 必须能访问所选目标；Tenshi 不会授予设备或文件夹权限。额外校验文件的错误单独记入报告；清理受阻时保留已保存的汇总文件。"),
   ("«Журнал ошибок» показывает технические записи в %LOCALAPPDATA%\\Tenshi\\Logs. Перед отправкой проверьте наличие личных путей.\n\n"
    "При проблемах сборки откройте tenshi-build.log и запустите check_windows.bat. run_tests.bat выполняет тесты отдельно; часть ошибок моделируется намеренно.\n\n"
    "EXE требует 64-битный Python 3.11+ и PyInstaller. Исходный архив не содержит готового EXE. Не повторяйте чтение неисправных дисков.\n\n"
    "Ошибки экспорта различают запрет доступа, назначение только для чтения, нехватку места и неподдерживаемые операции. «Invalid argument» не доказывает отсутствия прав; общие папки ВМ могут ограничивать операции. Исходное сообщение сохраняется. Flatpak нужен доступ к назначению; Tenshi не выдаёт права. Ошибки дополнительных сумм указываются отдельно; сохранённый сводный файл остаётся при блокировке очистки."),
   ("右上の「エラーログ」で技術記録を確認できます。Windows では通常 %LOCALAPPDATA%\\Tenshi\\Logs に保存されます。共有前に個人情報が含まれていないか確認してください。\n\n"
    "ビルドの問題は tenshi-build.log と check_windows.bat を確認します。run_tests.bat は別途テストを実行し、意図的なエラーが記録されることもあります。\n\n"
    "EXE の作成には64ビット Python 3.11+ と PyInstaller が必要です。ソース配布には EXE は含まれません。故障媒体の再読み取りは控えてください。\n\n"
    "出力エラーはアクセス拒否、読み取り専用の保存先、空き容量不足、未対応のファイル操作を区別します。「Invalid argument」だけでは書き込み権限不足と断定できず、VMの共有フォルダーで操作が制限される場合もあります。元の診断は保持します。Flatpakには保存先へのアクセスが必要で、Tenshiは権限を追加しません。チェックサムファイルのエラーは別に記録し、削除がブロックされた場合も保存済みの集約ファイルは保持します。"),
  )),
 'about': (
  ('Über Tenshi', 'About Tenshi', 'Acerca de Tenshi', '关于 Tenshi', 'О программе Tenshi', 'Tenshi について'),
  (
   ("Tenshi {version} – kostenlose, quelloffene Datenrettung und Analyse für Windows 10/11 (64 Bit) und Linux. Entwickelt von FreewareFuchs.\n\n"
    "Für Fragen und Verbesserungsvorschläge: kontakt@freewarefuchs.de\n\n"
    "Tenshi öffnet Quellmedien nur lesend. Gerettete Dateien und Images gehören auf einen anderen physischen Datenträger. Das Programm repariert kein Dateisystem am Quelldatenträger; ein bestätigter Export garantiert keine intakten ursprünglichen Dateiinhalte.\n\n"
    "Unterstützte Funktionen und Grenzen stehen in dieser Hilfe und der README. Quellcode und Lizenz (MIT): https://github.com/FreewareFuchs/Tenshi\n\n"
    "Website und Anleitungen: https://freewarefuchs.de/tenshi/"),
   ("Tenshi {version} – free, open-source data recovery and analysis for Windows 10/11 (64-bit) and Linux. Developed by FreewareFuchs.\n\n"
    "For questions and suggestions for improvement: kontakt@freewarefuchs.de\n\n"
    "Tenshi opens source media read-only. Save recovered files and images to a different physical disk. It does not repair the source filesystem, and a verified export does not guarantee intact original file contents.\n\n"
    "Supported features and limitations are described in this help and the README. Source code and MIT license: https://github.com/FreewareFuchs/Tenshi\n\n"
    "Website and guides: https://freewarefuchs.de/tenshi/"),
   ("Tenshi {version}: recuperación y análisis gratuitos y de código abierto para Windows 10/11 de 64 bits y Linux. Desarrollado por FreewareFuchs.\n\n"
    "Para preguntas y sugerencias de mejora: kontakt@freewarefuchs.de\n\n"
    "Tenshi abre los medios de origen en solo lectura. Guarde archivos e imágenes en otro disco físico. No repara el sistema de archivos de origen; confirmar una exportación no garantiza la integridad del contenido original.\n\n"
    "Las funciones y limitaciones se describen en esta ayuda y en README. Código fuente y licencia MIT: https://github.com/FreewareFuchs/Tenshi\n\n"
    "Sitio web y guías: https://freewarefuchs.de/tenshi/"),
   ("Tenshi {version}：适用于 Windows 10/11（64 位）与 Linux 的免费开源数据恢复和分析工具，由 FreewareFuchs 开发。\n\n"
    "如有问题或改进建议，请联系：kontakt@freewarefuchs.de\n\n"
    "Tenshi 以只读方式打开源介质。请将恢复的文件和镜像保存到另一块物理磁盘。它不会修复源文件系统；导出已确认不保证原始文件内容完整无损。\n\n"
    "支持的功能和限制见本帮助及 README。源代码与 MIT 许可证：https://github.com/FreewareFuchs/Tenshi\n\n"
    "网站与指南：https://freewarefuchs.de/tenshi/"),
   ("Tenshi {version} — бесплатная программа с открытым исходным кодом для восстановления и анализа данных в Windows 10/11 (64 бит) и Linux. Разработчик: FreewareFuchs.\n\n"
    "Вопросы и предложения по улучшению: kontakt@freewarefuchs.de\n\n"
    "Tenshi открывает источники только для чтения. Сохраняйте файлы и образы на другом физическом диске. Программа не исправляет исходную файловую систему; подтверждение экспорта не гарантирует целостность исходного содержимого.\n\n"
    "Возможности и ограничения описаны в справке и README. Исходный код и лицензия MIT: https://github.com/FreewareFuchs/Tenshi\n\n"
    "Сайт и руководства: https://freewarefuchs.de/tenshi/"),
   ("Tenshi {version} — Windows 10/11（64ビット）とLinux向けの無料・オープンソースのデータ復旧・解析ツールです。開発: FreewareFuchs。\n\n"
    "ご質問・改善のご提案: kontakt@freewarefuchs.de\n\n"
    "ソースメディアは読み取り専用で開きます。復旧ファイルやイメージは別の物理ディスクに保存してください。元のファイルシステムは修復せず、出力の確認も元の内容の完全性を保証しません。\n\n"
    "機能と制限はこのヘルプとREADMEで説明しています。ソースコードとMITライセンス: https://github.com/FreewareFuchs/Tenshi\n\n"
    "ウェブサイトとガイド: https://freewarefuchs.de/tenshi/"),
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
