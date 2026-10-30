"""Tenshi user-interface localization. The data engine keeps canonical values.

Translation is confined to UI labels, headings, dialog copy and display-only
StringVars. Disk paths, file names, search expressions and persisted export
metadata remain untouched. Unknown technical errors are shown verbatim.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk

LANGUAGES = {
    'de': 'Deutsch',
    'en': 'English',
    'es': 'Español',
    'zh': '中文（简体）',
    'ru': 'Русский',
    'ja': '日本語',
}

# German source -> English, Spanish, Simplified Chinese, Russian, Japanese.
# Keep these entries human-reviewable rather than translating filenames or
# filesystem metadata with an online service.
TRANSLATIONS = {}

def add(de, en, es, zh, ru, ja):
    TRANSLATIONS[de] = dict(zip(('en', 'es', 'zh', 'ru', 'ja'), (en, es, zh, ru, ja)))

add('System', 'System', 'Sistema', '系统', 'Система', 'システム')
add('Fortsetzen prüft fertige Dateien; unvollständige Dateien beginnen von vorn.',
    'Resume verifies completed files; incomplete files start from the beginning.',
    'Continuar verifica los archivos completos; los incompletos se copian desde el principio.',
    '继续时会检查已完成的文件；未完成的文件将从头复制。',
    'При продолжении готовые файлы проверяются, а неполные файлы копируются с начала.',
    '再開時は完了済みのファイルを検証し、未完了のファイルは最初からコピーします。')
add('Der bisherige Export kann nicht fortgesetzt werden: Quelle, Auswahl oder Exportordner wurde geändert. Bitte Quelle und Exportordner prüfen.',
    'The previous export cannot be resumed: the source, selection or export folder has changed. Please check the source and export folder.',
    'No se puede continuar la exportación anterior: cambió el origen, la selección o la carpeta de exportación. Compruebe el origen y la carpeta.',
    '无法继续之前的导出：来源、选择或导出文件夹已更改。请检查来源和导出文件夹。',
    'Невозможно продолжить предыдущий экспорт: изменён источник, выбор или папка экспорта. Проверьте источник и папку.',
    'ソース、選択内容、または出力フォルダーが変更されたため、前の出力を再開できません。ソースと出力フォルダーを確認してください。')
add('Pause','Pause','Pausar','暂停','Пауза','一時停止')
add('Fortsetzen','Resume','Continuar','继续','Продолжить','再開')
add('Export-Pause angefordert …','Export pause requested …','Pausa de exportación solicitada …','已请求暂停导出…','Запрошена пауза экспорта …','出力の一時停止を要求しました…')
add('Export pausiert.','Export paused.','Exportación en pausa.','导出已暂停。','Экспорт приостановлен.','出力を一時停止しました。')
add('Export wird fortgesetzt …','Resuming export …','Continuando exportación …','正在继续导出…','Продолжение экспорта …','出力を再開中…')
add('Pause erhält den aktuellen Stand, solange Tenshi geöffnet bleibt.',
    'Pause keeps the current progress while Tenshi remains open.',
    'La pausa conserva el progreso mientras Tenshi permanece abierto.',
    '暂停会保留当前进度，直到关闭 Tenshi。',
    'Пауза сохраняет текущий прогресс, пока Tenshi открыт.',
    'Tenshiを開いている間、一時停止中の進捗を保持します。')
add('Prüfsummendatei speichern …','Saving checksum file …','Guardando archivo de suma …','正在保存校验和文件…','Сохранение файла контрольной суммы …','チェックサムファイルを保存中…')
add('Prüfsummen zusammenfassen …','Consolidating checksums …','Agrupando sumas de comprobación …','正在汇总校验和…','Объединение контрольных сумм …','チェックサムを集約中…')
add('Prüfsummendateien konnten nicht vollständig gespeichert oder zusammengefasst werden. Vorhandene Einzeldateien bleiben nach Möglichkeit erhalten. Details:',
    'Checksum files could not be fully saved or consolidated. Existing individual files are retained where possible. Details:',
    'No se pudieron guardar o agrupar todas las sumas. Los archivos individuales existentes se conservan cuando es posible. Detalles:',
    '无法完整保存或汇总校验和文件。将尽可能保留现有的单独文件。详情：',
    'Не удалось полностью сохранить или объединить файлы контрольных сумм. Существующие отдельные файлы по возможности сохранены. Подробности:',
    'チェックサムファイルの保存または集約を完了できませんでした。既存の個別ファイルは可能な限り保持します。詳細:')

add('Vorhandene Datei prüfen','Verify existing file','Verificar archivo existente','检查现有文件','Проверка существующего файла','既存ファイルを検証')
add('Vorhandene Datei wird geprüft, nicht erneut kopiert.',
    'The existing file is being verified, not copied again.',
    'Se está verificando el archivo existente, sin volver a copiarlo.',
    '正在检查现有文件，不会重新复制。',
    'Существующий файл проверяется, а не копируется повторно.',
    '既存ファイルを検証中です。再コピーはしていません。')
add('Bestehender Export erkannt.','Existing export detected.','Exportación existente detectada.','已检测到现有导出。','Обнаружен существующий экспорт.','既存の出力を検出しました。')
add('Unvollständige Dateien beginnen beim Fortsetzen von vorn.',
    'Incomplete files are copied from the beginning when resuming.',
    'Los archivos incompletos se copian desde el principio al continuar.',
    '继续导出时，未完成的文件将从头复制。',
    'При продолжении неполные файлы копируются с начала.',
    '再開時、未完了のファイルは最初からコピーします。')
add('{count} ausgewählte Einträge samt Unterordnern exportieren?\n\nZielordner: {target}\n\nZum Fortsetzen nach einem Programmneustart dieselbe Quelle und Auswahl sowie denselben ursprünglichen Zielordner wählen. Fertige Dateien werden geprüft. Unvollständige Dateien beginnen von vorn. Vorhandene fremde Dateien bleiben unangetastet.',
    'Export {count} selected entries including subfolders?\n\nDestination folder: {target}\n\nTo resume after restarting Tenshi, use the same source, selection and original destination folder. Completed files are verified. Incomplete files are copied from the beginning. Unrelated existing files are left untouched.',
    '¿Exportar {count} entradas seleccionadas y sus subcarpetas?\n\nCarpeta de destino: {target}\n\nPara continuar después de reiniciar Tenshi, use el mismo origen, selección y carpeta de destino original. Los archivos completos se verifican. Los incompletos se copian desde el principio. Los archivos existentes ajenos no se modifican.',
    '导出所选的 {count} 个条目及其子文件夹？\n\n目标文件夹：{target}\n\n重启 Tenshi 后继续时请使用相同的来源、选择和原始目标文件夹。已完成的文件会进行检查。未完成的文件将从头复制。其他现有文件保持不变。',
    'Экспортировать выбранные элементы ({count}) с вложенными папками?\n\nПапка назначения: {target}\n\nДля продолжения после перезапуска Tenshi выберите тот же источник, набор элементов и исходную папку назначения. Готовые файлы проверяются. Неполные файлы копируются с начала. Посторонние существующие файлы не изменяются.',
    '選択した {count} 件とサブフォルダーを出力しますか？\n\n保存先フォルダー: {target}\n\n再起動後に再開する場合は同じソース、選択内容、元の保存先フォルダーを指定してください。完了済みのファイルは検証し、未完了のファイルは最初からコピーします。無関係な既存ファイルは変更しません。')

# Non-modal export window: format translated templates before adding filenames.
add('Tenshi – Exportfortschritt', 'Tenshi – Export progress', 'Tenshi – Progreso de exportación', 'Tenshi – 导出进度', 'Tenshi – Ход экспорта', 'Tenshi – 出力の進捗')
add('Fortschrittsfenster', 'Progress window', 'Ventana de progreso', '进度窗口', 'Окно прогресса', '進捗ウィンドウ')
add('Fortschritt / Ergebnis', 'Progress / result', 'Progreso / resultado', '进度 / 结果', 'Прогресс / результат', '進捗 / 結果')
add('SHA256 wird während des Kopierens berechnet.', 'SHA256 is calculated while copying.', 'SHA256 se calcula durante la copia.', '复制时计算 SHA256。', 'SHA256 вычисляется при копировании.', 'コピー中に SHA256 を計算します。')
add('SHA256-Prüfung der Zieldatei läuft …', 'SHA256 verification of the destination file is running …', 'Verificando SHA256 del archivo de destino …', '正在对目标文件进行 SHA256 验证…', 'Выполняется проверка SHA256 целевого файла …', '出力先ファイルの SHA256 を検証中…')
add('SHA256: Details im Ergebnisbericht.', 'SHA256: see the results report for details.', 'SHA256: detalles en el informe de resultados.', 'SHA256：详情见结果报告。', 'SHA256: подробности в отчёте о результатах.', 'SHA256：詳細は結果レポートを参照してください。')
add('Zielordner öffnen', 'Open destination folder', 'Abrir carpeta de destino', '打开目标文件夹', 'Открыть папку назначения', '出力先フォルダーを開く')
add('Offen', 'Pending', 'Pendiente', '待处理', 'Ожидает', '未処理')
add('Kopiert, noch ungeprüft', 'Copied, not yet verified', 'Copiado, sin verificar', '已复制，尚未验证', 'Скопировано, не проверено', 'コピー済み、未検証')
add('Export bestätigt', 'Export verified', 'Exportación verificada', '导出已验证', 'Экспорт подтверждён', '出力を検証済み')
add('Fehler im Export', 'Export error', 'Error de exportación', '导出错误', 'Ошибка экспорта', '出力エラー')
add('Nicht bestätigt', 'Not verified', 'Sin verificar', '未验证', 'Не подтверждено', '未検証')
add('Gemischt / teilweise', 'Mixed / partial', 'Mixto / parcial', '混合 / 部分', 'Смешанное / частично', '混在 / 一部')
add('Export wird abgeschlossen …', 'Finalizing export …', 'Finalizando exportación …', '正在完成导出…', 'Завершение экспорта …', '出力を完了処理中…')
add('Export läuft …', 'Export in progress …', 'Exportación en curso …', '正在导出…', 'Экспорт выполняется …', '出力中…')
add('Export-Abbruch angefordert …', 'Export cancellation requested …', 'Cancelación de exportación solicitada …', '已请求取消导出…', 'Запрошена отмена экспорта …', '出力の中止を要求しました…')
add('Laufzeit: {duration}', 'Elapsed: {duration}', 'Tiempo transcurrido: {duration}', '已用时间：{duration}', 'Прошло: {duration}', '経過時間：{duration}')
add('Neu übertragen: {size} · Kopiertempo: {rate}/s', 'Newly transferred: {size} · Copy rate: {rate}/s', 'Transferido nuevo: {size} · Velocidad: {rate}/s', '本次传输：{size} · 复制速度：{rate}/s', 'Передано заново: {size} · Скорость: {rate}/s', '今回の転送：{size} · コピー速度：{rate}/s')
add('SHA256-Lesestand der aktuellen Datei: {percent:.1f} %', 'Current file SHA256 read progress: {percent:.1f} %', 'Lectura SHA256 del archivo actual: {percent:.1f} %', '当前文件 SHA256 读取进度：{percent:.1f} %', 'Чтение SHA256 текущего файла: {percent:.1f} %', '現在のファイルの SHA256 読み取り進捗：{percent:.1f} %')
add('Export bestätigt: {percent:.1f} %', 'Export verified: {percent:.1f} %', 'Exportación verificada: {percent:.1f} %', '导出已验证：{percent:.1f} %', 'Экспорт подтверждён: {percent:.1f} %', '出力を検証済み：{percent:.1f} %')
add('Kopier-Restzeit ca. {duration}', 'Estimated copy time left: {duration}', 'Tiempo de copia restante aprox.: {duration}', '预计剩余复制时间：{duration}', 'Осталось копировать примерно: {duration}', 'コピーの推定残り時間：{duration}')
add('Einträge: {done} von {total} · Fehler: {errors} · Übersprungen: {skipped}', 'Items: {done} of {total} · Errors: {errors} · Skipped: {skipped}', 'Entradas: {done} de {total} · Errores: {errors} · Omitidas: {skipped}', '条目：{done} / {total} · 错误：{errors} · 已跳过：{skipped}', 'Записи: {done} из {total} · Ошибки: {errors} · Пропущено: {skipped}', '項目：{done} / {total} · エラー：{errors} · スキップ：{skipped}')
add('Aktuelle Datei: {path}', 'Current file: {path}', 'Archivo actual: {path}', '当前文件：{path}', 'Текущий файл: {path}', '現在のファイル：{path}')
add('100 Felder = 100 % der Einträge.', '100 cells = 100% of items.', '100 celdas = 100 % de las entradas.', '100 个格子 = 全部条目。', '100 ячеек = 100 % записей.', '100 マス = 全項目の 100%。')
add('Noch kein Exportplan vorhanden.', 'No export plan yet.', 'Todavía no hay un plan de exportación.', '尚无导出计划。', 'План экспорта ещё не создан.', '出力計画はまだありません。')
add('Exportplan enthält keine Einträge.', 'The export plan has no items.', 'El plan de exportación no contiene entradas.', '导出计划中没有条目。', 'В плане экспорта нет записей.', '出力計画に項目がありません。')
add('100 Felder = 100 % der geplanten Dateigrößen.', '100 cells = 100% of planned file sizes.', '100 celdas = 100 % de los tamaños de archivo previstos.', '100 个格子 = 计划文件大小的 100%。', '100 ячеек = 100 % запланированного объёма файлов.', '100 マス = 予定されたファイルサイズの 100%。')
add('Exportanteile, keine Datenträgersektoren.', 'Export portions, not disk sectors.', 'Partes de la exportación, no sectores del disco.', '表示导出份额，并非磁盘扇区。', 'Доли экспорта, а не секторы диска.', '出力の割合であり、ディスクセクターではありません。')
add('Bestätigung betrifft den Export, nicht den Originalinhalt.', 'Verification covers the export, not the original content.', 'La verificación cubre la exportación, no el contenido original.', '验证针对导出结果，并非原始内容。', 'Подтверждение относится к экспорту, а не к исходному содержимому.', '検証の対象は出力結果であり、元の内容ではありません。')
add('Prüfumfang', 'Verification scope', 'Alcance de verificación', '验证范围', 'Область проверки', '検証の範囲')
add('Quellzuordnung des Exports fehlt.', 'Export source mapping is missing.', 'Falta la asignación de origen de la exportación.', '缺少导出源映射。', 'Отсутствует привязка источника экспорта.', '出力元の対応情報がありません。')

# Unified source picker: display-only labels, never translate source paths.
add('Datenträger oder Laufwerk auswählen', 'Select disk or volume', 'Seleccionar disco o volumen', '选择磁盘或卷', 'Выбрать диск или том', 'ディスクまたはボリュームを選択')
add('Datenträger oder Laufwerk auswählen – nur lesen', 'Select disk or volume — read only', 'Seleccionar disco o volumen — solo lectura', '选择磁盘或卷 — 只读', 'Выбрать диск или том — только чтение', 'ディスクまたはボリュームを選択 — 読み取り専用')
add('Ein gesamter Datenträger umfasst alle Partitionen. Ein Laufwerk umfasst nur das ausgewählte Volume. Zugeordnete Laufwerke stehen unter ihrem Datenträger.', 'A whole disk includes all partitions. A volume includes only the selected volume. Mapped volumes appear under their disk.', 'Un disco completo incluye todas las particiones. Un volumen abarca solo el volumen seleccionado. Los volúmenes asociados aparecen bajo su disco.', '整个磁盘包含所有分区。卷仅包含所选卷。已确定所属磁盘的卷显示在该磁盘下方。', 'Весь диск включает все разделы. Том охватывает только выбранный том. Связанные тома показаны под своим диском.', 'ディスク全体にはすべてのパーティションが含まれます。ボリュームは選択した領域のみが対象です。対応するボリュームはディスクの下に表示されます。')
add('Datenträger', 'Disk', 'Disco', '磁盘', 'Диск', 'ディスク')
add('Quelle', 'Source', 'Origen', '源', 'Источник', 'ソース')
add('Umfang', 'Scope', 'Alcance', '范围', 'Область', '対象範囲')
add('Gesamter Datenträger', 'Whole disk', 'Disco completo', '整个磁盘', 'Весь диск', 'ディスク全体')
add('Laufwerk / Partition', 'Volume / partition', 'Volumen / partición', '卷 / 分区', 'Том / раздел', 'ボリューム / パーティション')
add('Laufwerk (mehrere Datenträger)', 'Volume (multiple disks)', 'Volumen (varios discos)', '卷（跨多个磁盘）', 'Том (несколько дисков)', 'ボリューム（複数ディスク）')
add('Laufwerke ohne eindeutige Zuordnung', 'Volumes without a unique disk mapping', 'Volúmenes sin un disco asociado único', '无法唯一确定所属磁盘的卷', 'Тома без однозначной привязки к диску', 'ディスクを一意に特定できないボリューム')
add('Bitte einen Datenträger oder ein Laufwerk markieren.', 'Select a disk or volume.', 'Seleccione un disco o volumen.', '请选择磁盘或卷。', 'Выберите диск или том.', 'ディスクまたはボリュームを選択してください。')
add('Quellen werden ermittelt …', 'Discovering sources …', 'Buscando orígenes …', '正在查找源…', 'Поиск источников …', 'ソースを検索中…')
add('Quellen konnten nicht ermittelt werden.', 'Sources could not be discovered.', 'No se pudieron detectar los orígenes.', '无法查找源。', 'Не удалось найти источники.', 'ソースを検索できませんでした。')
add('Keine Quellen erkannt. Ein vorhandenes Image kann weiterhin geöffnet werden.', 'No sources found. You can still open an existing image.', 'No se encontraron orígenes. Puede abrir una imagen existente.', '未找到源。仍可打开现有镜像。', 'Источники не найдены. Можно открыть существующий образ.', 'ソースが見つかりません。既存のイメージは開けます。')
add('Datenträgerliste konnte nicht vollständig ermittelt werden.', 'The disk list could not be fully retrieved.', 'No se pudo obtener la lista completa de discos.', '无法获取完整的磁盘列表。', 'Не удалось получить полный список дисков.', 'ディスク一覧を完全に取得できませんでした。')
add('Laufwerksliste konnte nicht vollständig ermittelt werden.', 'The volume list could not be fully retrieved.', 'No se pudo obtener la lista completa de volúmenes.', '无法获取完整的卷列表。', 'Не удалось получить полный список томов.', 'ボリューム一覧を完全に取得できませんでした。')
add('Die Auflistung bestätigt keine Leserechte. Für das tatsächliche Einlesen beider Quelltypen können Windows-Administratorrechte erforderlich sein.', 'Being listed does not confirm read access. Reading either source type may require Windows administrator privileges.', 'Aparecer en la lista no confirma permisos de lectura. Ambos tipos de origen pueden requerir privilegios de administrador de Windows.', '列出设备不代表具有读取权限。实际读取这两种源都可能需要 Windows 管理员权限。', 'Наличие в списке не подтверждает право чтения. Для чтения обоих типов источников могут требоваться права администратора Windows.', '一覧表示は読み取り権限を保証しません。どちらのソースも読み取りに Windows 管理者権限が必要な場合があります。')
add('Die Auflistung bestätigt keine Leserechte. Geräteberechtigungen gezielt prüfen lassen oder ein Image öffnen. Tenshi ohne sudo starten.', 'Being listed does not confirm read access. Have device permissions checked specifically or open an image. Start Tenshi without sudo.', 'Aparecer en la lista no confirma permisos de lectura. Revise los permisos del dispositivo o abra una imagen. Inicie Tenshi sin sudo.', '列出设备不代表具有读取权限。请针对该设备检查权限，或打开镜像。启动 Tenshi 时不要使用 sudo。', 'Наличие в списке не подтверждает право чтения. Проверьте права конкретного устройства или откройте образ. Запускайте Tenshi без sudo.', '一覧表示は読み取り権限を保証しません。対象デバイスの権限を確認するか、イメージを開いてください。Tenshi は sudo を使わず起動してください。')
add('Eingehängte Dateisysteme können sich durch das Betriebssystem verändern. Bei defekten Datenträgern weitere Lesezugriffe minimieren und zuerst ein Image erstellen.', 'The operating system may change mounted filesystems. Minimize further reads of damaged disks and create an image first.', 'El sistema operativo puede modificar los sistemas de archivos montados. Minimice las lecturas de discos dañados y cree primero una imagen.', '操作系统可能会更改已挂载的文件系统。对于损坏的磁盘，请尽量减少读取并先创建镜像。', 'ОС может изменять подключённые файловые системы. Сократите чтение повреждённых дисков и сначала создайте образ.', 'マウント済みのファイルシステムは OS により変更される場合があります。故障したディスクの読み取りを最小限にし、先にイメージを作成してください。')
add('Tenshi öffnet die Quelle ausschließlich lesend. Weitere Lesezugriffe können defekte Datenträger belasten. Quelle übernehmen?', 'Tenshi opens the source read only. Further reads may strain damaged disks. Use this source?', 'Tenshi abre el origen solo para lectura. Más lecturas pueden afectar a discos dañados. ¿Usar este origen?', 'Tenshi 仅以只读方式打开源。进一步读取可能加重损坏磁盘的负担。是否使用此源？', 'Tenshi открывает источник только для чтения. Чтение может дополнительно нагрузить повреждённый диск. Использовать источник?', 'Tenshi はソースを読み取り専用で開きます。追加の読み取りは故障したディスクに負荷をかける場合があります。このソースを使用しますか？')
add('Quelle nicht lesbar', 'Source cannot be read', 'No se puede leer el origen', '无法读取源', 'Источник недоступен для чтения', 'ソースを読み取れません')
add('Für direkte Lesezugriffe auf Datenträger und Laufwerke Windows-Administratorrechte prüfen oder ein Image öffnen.', 'For direct reads of disks and volumes, check Windows administrator privileges or open an image.', 'Para leer discos y volúmenes directamente, compruebe los privilegios de administrador de Windows o abra una imagen.', '直接读取磁盘和卷时，请检查 Windows 管理员权限，或打开镜像。', 'Для прямого чтения дисков и томов проверьте права администратора Windows или откройте образ.', 'ディスクやボリュームの直接読み取りには Windows 管理者権限を確認するか、イメージを開いてください。')
add('Geräteberechtigungen gezielt prüfen lassen oder ein Image öffnen. Tenshi ohne sudo starten.', 'Have device permissions checked specifically or open an image. Start Tenshi without sudo.', 'Revise los permisos del dispositivo o abra una imagen. Inicie Tenshi sin sudo.', '请针对该设备检查权限，或打开镜像。启动 Tenshi 时不要使用 sudo。', 'Проверьте права конкретного устройства или откройте образ. Запускайте Tenshi без sudo.', '対象デバイスの権限を確認するか、イメージを開いてください。Tenshi は sudo を使わず起動してください。')

# Explicit transfer and checksum phases for batch export progress.
add('Datei kopieren', 'Copying file', 'Copiando archivo', '正在复制文件', 'Копирование файла', 'ファイルをコピー中')
add('SHA256 prüfen', 'Checking SHA256', 'Comprobando SHA256', '正在校验 SHA256', 'Проверка SHA256', 'SHA256 を検査中')

# Copied-stream checkpoints authorize verification only, never overwriting.
add('Neue Exporte: Zieldatei mit der Prüfsumme des kopierten Datenstroms verglichen. Kein Nachweis ursprünglicher Integrität.',
    'New exports: destination compared with the checksum of the copied data stream. Not proof of original integrity.',
    'Nuevas exportaciones: destino comparado con la suma del flujo de datos copiado. No demuestra la integridad original.',
    '新导出：将目标文件与已复制数据流的校验和比较。这不能证明原始数据完整。',
    'Новые экспорты: файл назначения сравнен с контрольной суммой скопированного потока. Это не доказывает исходную целостность.',
    '新規出力：コピーしたデータストリームのチェックサムと出力先を比較。元データの完全性の証明ではありません。')
add('Fortsetzen: Größe und SHA-256 mit dem gespeicherten Prüfwert verglichen. Kein erneutes Lesen der Quelle für den Inhaltsvergleich.',
    'Resume: size and SHA-256 compared with the saved checksum. The source is not reread for this content comparison.',
    'Reanudación: tamaño y SHA-256 comparados con la suma guardada. No se relee el origen para esta comparación del contenido.',
    '继续：将大小和 SHA-256 与保存的校验值比较。此次内容比较不会重新读取源。',
    'Продолжение: размер и SHA-256 сравнены с сохранённой суммой. Источник не перечитывается для этого сравнения содержимого.',
    '再開：サイズとSHA-256を保存した値と比較。この内容比較のためにソースを再読込しません。')
add('Mit der beim Kopieren gespeicherten Prüfsumme bestätigt',
    'Confirmed against the checksum saved during copying',
    'Confirmado con la suma guardada durante la copia',
    '已通过复制时保存的校验和确认',
    'Подтверждено по сумме, сохранённой при копировании',
    'コピー時に保存したチェックサムで確認済み')
add('Zieldatei stimmt nicht mit den kopierten Daten überein.',
    'Destination does not match the copied data.',
    'El destino no coincide con los datos copiados.',
    '目标文件与复制的数据不一致。',
    'Файл назначения не соответствует скопированным данным.',
    '出力先がコピーしたデータと一致しません。')

add('Exportdatei während der Prüfung geändert.',
    'Export file changed during verification.',
    'El archivo exportado cambió durante la comprobación.',
    '导出文件在校验期间发生变化。',
    'Экспортированный файл изменён во время проверки.',
    '検証中に出力ファイルが変更されました。')

# Batch completion must distinguish failed exports from successful processing.
add('Beendet mit Fehlern', 'Completed with errors', 'Finalizado con errores', '完成，但有错误', 'Завершено с ошибками', 'エラーありで終了')
add('Beim Stapel-Export sind {count} Fehler aufgetreten. Nicht alle Dateien konnten exportiert oder bestätigt werden. Details stehen im Ergebnisbericht.',
    'Batch export encountered {count} errors. Not all files could be exported or verified. See the result report for details.',
    'La exportación por lotes encontró {count} errores. No se pudieron exportar o verificar todos los archivos. Consulte los detalles en el informe de resultados.',
    '批量导出发生 {count} 个错误。部分文件无法导出或验证。详情请查看结果报告。',
    'При пакетном экспорте возникло ошибок: {count}. Не все файлы удалось экспортировать или проверить. Подробности в отчёте о результатах.',
    '一括エクスポートで{count}件のエラーが発生しました。一部のファイルをエクスポートまたは検証できませんでした。詳細は結果レポートをご覧ください。')

# Optional read-only CRC/structure verification of exported ZIP files.
add('Exportierte ZIP-Datei prüfen …', 'Check exported ZIP file …', 'Comprobar ZIP exportado …', '检查导出的 ZIP 文件…', 'Проверить экспортированный ZIP…', 'エクスポートしたZIPを検査…')
add('ZIP-Inhaltsprüfung', 'ZIP content check', 'Comprobación del contenido ZIP', 'ZIP 内容检查', 'Проверка содержимого ZIP', 'ZIP内容検査')
add('Prüft ZIP-Struktur und interne CRC-Prüfsummen. Kein Vergleich mit dem Original und keine Prüfung des Inhaltsformats enthaltener Dateien.',
    'Checks ZIP structure and internal CRC checksums. No comparison with the original and no validation of the formats of contained files.',
    'Comprueba la estructura ZIP y las sumas CRC internas. No compara con el original ni valida el formato de los archivos contenidos.',
    '检查 ZIP 结构和内部 CRC 校验和。不与原文件比较，也不验证所含文件的内容格式。',
    'Проверяет структуру ZIP и внутренние суммы CRC. Не сравнивает с оригиналом и не проверяет формат содержимого вложенных файлов.',
    'ZIP構造と内部CRCを検査します。元ファイルとの比較や、格納ファイルの内容形式の検証は行いません。')
add('Grenzen: 512 MiB Archiv, 512 MiB entpackte Daten, 10.000 Einträge.',
    'Limits: 512 MiB archive, 512 MiB expanded data, 10,000 entries.',
    'Límites: archivo de 512 MiB, datos descomprimidos de 512 MiB, 10.000 entradas.',
    '限制：压缩文件 512 MiB，解压数据 512 MiB，10,000 个条目。',
    'Ограничения: архив 512 МиБ, распакованные данные 512 МиБ, 10 000 записей.',
    '上限：アーカイブ512 MiB、展開データ512 MiB、10,000項目。')
add('ZIP-Inhalt wird geprüft …', 'Checking ZIP content …', 'Comprobando contenido ZIP …', '正在检查 ZIP 内容…', 'Проверка содержимого ZIP…', 'ZIP内容を検査中…')
add('Nur reguläre Dateien können geprüft werden.', 'Only regular files can be checked.', 'Solo se pueden comprobar archivos regulares.', '只能检查普通文件。', 'Можно проверять только обычные файлы.', '通常のファイルのみ検査できます。')
add('ZIP-Prüfgrenze erreicht. Keine vollständige Prüfung.', 'ZIP check limit reached. Check incomplete.', 'Se alcanzó el límite de comprobación ZIP. Comprobación incompleta.', '已达到 ZIP 检查限制。检查不完整。', 'Достигнут лимит проверки ZIP. Проверка неполная.', 'ZIP検査の上限に達しました。検査は未完了です。')
add('Verschlüsselte ZIP-Inhalte werden nicht geprüft.', 'Encrypted ZIP content is not checked.', 'No se comprueba el contenido ZIP cifrado.', '不检查加密的 ZIP 内容。', 'Зашифрованное содержимое ZIP не проверяется.', '暗号化されたZIPの内容は検査しません。')
add('Datei während der Prüfung geändert. Keine Bestätigung möglich.', 'File changed during the check. No confirmation possible.', 'El archivo cambió durante la comprobación. No se puede confirmar.', '文件在检查期间发生变化。无法确认。', 'Файл изменён во время проверки. Подтверждение невозможно.', '検査中にファイルが変更されました。確認できません。')
add('ZIP-Struktur und CRC-Prüfsummen ohne Fehler geprüft.', 'ZIP structure and CRC checksums checked without errors.', 'Estructura ZIP y sumas CRC comprobadas sin errores.', 'ZIP 结构和 CRC 校验和检查未发现错误。', 'Структура ZIP и суммы CRC проверены без ошибок.', 'ZIP構造とCRCの検査でエラーは見つかりませんでした。')
add('ZIP beschädigt, unvollständig oder kein unterstütztes ZIP-Archiv.', 'ZIP damaged, incomplete, or not a supported ZIP archive.', 'ZIP dañado, incompleto o no compatible.', 'ZIP 已损坏、不完整或不是受支持的 ZIP 压缩文件。', 'ZIP повреждён, неполон или не является поддерживаемым ZIP-архивом.', 'ZIPが破損、不完全、または対応するZIP形式ではありません。')
add('ZIP-Kompression wird nicht unterstützt. Keine vollständige Prüfung.', 'ZIP compression is unsupported. Check incomplete.', 'Compresión ZIP no compatible. Comprobación incompleta.', '不支持此 ZIP 压缩方式。检查不完整。', 'Сжатие ZIP не поддерживается. Проверка неполная.', 'ZIP圧縮方式に対応していません。検査は未完了です。')
add('Datei konnte nicht vollständig gelesen werden.', 'The file could not be read completely.', 'No se pudo leer el archivo por completo.', '无法完整读取文件。', 'Не удалось полностью прочитать файл.', 'ファイルを完全に読み取れませんでした。')
add('Geprüfte Dateien', 'Checked files', 'Archivos comprobados', '已检查文件', 'Проверено файлов', '検査済みファイル')
add('Prüfung abgebrochen.', 'Check cancelled.', 'Comprobación cancelada.', '检查已取消。', 'Проверка отменена.', '検査を中止しました。')

# exFAT sessions created before initialized-length tracking require a new scan.
add('exFAT-ValidDataLength fehlt oder ist ungültig. Quelle erneut einlesen.',
    'exFAT ValidDataLength is missing or invalid. Scan the source again.',
    'Falta ValidDataLength de exFAT o no es válido. Vuelva a analizar el origen.',
    'exFAT ValidDataLength 缺失或无效。请重新扫描源。',
    'Значение exFAT ValidDataLength отсутствует или неверно. Повторно просканируйте источник.',
    'exFATのValidDataLengthが不明または無効です。ソースを再スキャンしてください。')
add('exFAT-ValidDataLength fehlt. Quelle erneut einlesen.',
    'exFAT ValidDataLength is missing. Scan the source again.',
    'Falta ValidDataLength de exFAT. Vuelva a analizar el origen.',
    'exFAT ValidDataLength 缺失。请重新扫描源。',
    'Значение exFAT ValidDataLength отсутствует. Повторно просканируйте источник.',
    'exFATのValidDataLengthが不明です。ソースを再スキャンしてください。')

# Device identity mismatch and loss during read-only operations.
add('Datenträger wurde ausgetauscht oder geändert. Quelle erneut einlesen.',
    'The device was replaced or changed. Scan the source again.',
    'El dispositivo se ha sustituido o modificado. Vuelva a analizar el origen.',
    '设备已被更换或发生变化。请重新扫描源。',
    'Устройство заменено или изменено. Повторно просканируйте источник.',
    'デバイスが交換または変更されました。ソースを再スキャンしてください。')
add('Quelle nicht mehr erreichbar. Datenträger erneut einlesen.',
    'The source is no longer accessible. Scan the device again.',
    'El origen ya no está accesible. Vuelva a analizar el dispositivo.',
    '源已无法访问。请重新扫描设备。',
    'Источник больше недоступен. Повторно просканируйте устройство.',
    'ソースにアクセスできなくなりました。デバイスを再スキャンしてください。')
add('Datenträgerkennung konnte nicht vollständig gelesen werden.',
    'The device identifier could not be read completely.',
    'No se pudo leer por completo el identificador del dispositivo.',
    '无法完整读取设备标识。',
    'Не удалось полностью прочитать идентификатор устройства.',
    'デバイス識別情報を完全に読み取れませんでした。')

# Partition detection confidence is separate from recovery prospects.
add('Partitionserkennung: hohe Plausibilität', 'Partition detection: high plausibility', 'Detección de partición: plausibilidad alta', '分区识别：高可信度', 'Обнаружение раздела: высокая достоверность', 'パーティション検出：高い妥当性')
add('Partitionserkennung: mittlere Plausibilität', 'Partition detection: medium plausibility', 'Detección de partición: plausibilidad media', '分区识别：中等可信度', 'Обнаружение раздела: средняя достоверность', 'パーティション検出：中程度の妥当性')
add('Partitionserkennung: geringe Plausibilität', 'Partition detection: low plausibility', 'Detección de partición: plausibilidad baja', '分区识别：低可信度', 'Обнаружение раздела: низкая достоверность', 'パーティション検出：低い妥当性')
add('Diese Bewertung sagt nichts über den Zustand der Dateien oder die Rettungschancen aus.',
    'This rating says nothing about the condition of the files or the chances of recovery.',
    'Esta valoración no indica el estado de los archivos ni las posibilidades de recuperación.',
    '此评级不反映文件状况或恢复成功的可能性。',
    'Эта оценка ничего не говорит о состоянии файлов или шансах восстановления.',
    'この評価は、ファイルの状態や復元の見込みを示すものではありません。')

# Online-independent help access (Tenshi 3.0.0)
add('Hilfe', 'Help', 'Ayuda', '帮助', 'Справка', 'ヘルプ')

# Local support snapshot
add('Support-Bericht', 'Support report', 'Informe de soporte', '支持报告', 'Отчёт для поддержки', 'サポートレポート')
add('Support-Bericht speichern', 'Save support report', 'Guardar informe de soporte', '保存支持报告', 'Сохранить отчёт для поддержки', 'サポートレポートを保存')
add('Vorschau: technische Metadaten und Fehlercodes. Keine Pfade, Dateinamen oder Dateiinhalte. Der Bericht wird nur lokal gespeichert.',
    'Preview: technical metadata and error codes. No paths, filenames or file contents. The report is saved locally only.',
    'Vista previa: metadatos técnicos y códigos de error. Sin rutas, nombres ni contenido de archivos. Solo se guarda localmente.',
    '预览：技术元数据和错误代码。不含路径、文件名或文件内容。报告仅保存在本地。',
    'Предпросмотр: технические метаданные и коды ошибок. Без путей, имён и содержимого файлов. Отчёт сохраняется только локально.',
    'プレビュー：技術メタデータとエラーコード。パス、ファイル名、ファイル内容は含みません。保存先はローカルのみです。')

add('Sonstige MFT-Auswertungsfehler', 'Other MFT parsing errors', 'Otros errores de interpretación MFT', '其他 MFT 解析错误', 'Другие ошибки разбора MFT', 'その他のMFT解析エラー')
add('Gelöschte Records: Clusterverweise außerhalb des Volumes', 'Deleted records: cluster references outside the volume', 'Registros borrados: referencias a clústeres fuera del volumen', '已删除记录：簇引用超出卷范围', 'Удалённые записи: ссылки на кластеры за пределами тома', '削除済みレコード：ボリューム外のクラスタ参照')
add('Diese Löschverweise können veraltet sein, etwa nach einer Partitionsverkleinerung. Die Ursache ist nicht nachgewiesen. Betroffene Einträge bleiben nicht exportierbar.',
    'These deleted-file references may be stale, for example after shrinking a partition. The cause is not proven. Affected entries remain unavailable for export.',
    'Estas referencias de archivos borrados pueden estar obsoletas, por ejemplo tras reducir una partición. La causa no está demostrada. Las entradas afectadas no se pueden exportar.',
    '这些删除文件的引用可能已过时，例如在缩小分区后。原因尚未证实。相关记录仍无法导出。',
    'Эти ссылки удалённых файлов могут устареть, например после уменьшения раздела. Причина не доказана. Экспорт затронутых записей остаётся недоступен.',
    'これらの削除ファイル参照は、パーティション縮小後などに古くなっている可能性があります。原因は未確定です。該当レコードは引き続きエクスポートできません。')

# NTFS diagnostics distinguish interpretation failures from read failures.
add('nicht auswertbare und', 'unparsed and', 'no interpretados y', '无法解析及', 'не разобрано и', '解析不能、および')
add('MFT-Auswertungsfehler', 'MFT parsing errors', 'Errores de interpretación MFT', 'MFT 解析错误', 'Ошибки разбора MFT', 'MFT解析エラー')
add('MFT-Lesefehler', 'MFT read errors', 'Errores de lectura MFT', 'MFT 读取错误', 'Ошибки чтения MFT', 'MFT読み取りエラー')
add('Attributlisten-Limit: nicht untersuchte Basisrecords', 'Attribute-list limit: unexamined base records', 'Límite de listas de atributos: registros base no examinados', '属性列表上限：未检查的基础记录', 'Лимит списков атрибутов: непроверенные базовые записи', '属性リスト上限：未調査の基本レコード')
add('Verzeichnisindex-Auswertungsmeldungen', 'Directory index parsing notices', 'Avisos de interpretación de índices de directorio', '目录索引解析提示', 'Сообщения разбора индексов каталогов', 'ディレクトリ索引の解析通知')
add('Die Dateiliste kann unvollständig sein. Auswertungsfehler oder erreichte Limits beweisen keinen Datenträgerschaden. Details: Diagnose… → Analysebericht speichern.',
    'The file list may be incomplete. Parsing errors or reached limits do not prove drive damage. Details: Diagnostics… → Save analysis report.',
    'La lista puede estar incompleta. Los errores de interpretación o límites alcanzados no demuestran daños en la unidad. Detalles: Diagnóstico… → Guardar informe de análisis.',
    '文件列表可能不完整。解析错误或达到上限并不能证明磁盘损坏。详情：诊断… → 保存分析报告。',
    'Список файлов может быть неполным. Ошибки разбора или достижение лимитов не доказывают повреждение диска. Подробности: Диагностика… → Сохранить отчёт анализа.',
    'ファイル一覧は不完全な可能性があります。解析エラーや上限到達だけではディスクの損傷を証明しません。詳細：診断… → 解析レポートを保存。')

# Imaging controls (Tenshi 2.7.0)
add('Leseversuche:', 'Read retries:', 'Reintentos:', '重试读取：', 'Повторы чтения:', '再読み取り回数:')
add('Bei Medienfehler:', 'On media error:', 'Ante error del medio:', '介质错误时：', 'При ошибке носителя:', '媒体エラー時:')
add('Nullen + protokollieren', 'Fill with zeros + log', 'Rellenar ceros y registrar', '填零并记录', 'Заполнить нулями и записать', 'ゼロで埋めて記録')
add('Sicher anhalten', 'Stop safely', 'Detener con seguridad', '安全停止', 'Безопасно остановить', '安全に停止')
add('Fehlerstellen-Bericht', 'Bad-sector report', 'Informe de sectores defectuosos', '坏扇区报告', 'Отчёт о сбойных секторах', '不良セクターのレポート')
add('Bericht speichern', 'Save report', 'Guardar informe', '保存报告', 'Сохранить отчёт', 'レポートを保存')
add('Bericht gespeichert.', 'Report saved.', 'Informe guardado.', '报告已保存。', 'Отчёт сохранён.', 'レポートを保存しました。')
add('Tenshi – Fehlerstellen-Bericht', 'Tenshi – Bad-sector report', 'Tenshi – Informe de sectores defectuosos', 'Tenshi – 坏扇区报告', 'Tenshi – Отчёт о сбойных секторах', 'Tenshi – 不良セクターのレポート')
add('Optional 0–3 erneute Leseversuche an defekten Sektoren; jeder Versuch belastet das Medium. Bei Nullen entstehen Datenlücken; sicherer Stopp belässt den letzten gültigen Prüfpunkt.',
    'Optional 0–3 retries on failed sectors; every attempt stresses the medium. Zero fill causes data gaps; a safe stop preserves the last checkpoint.',
    'De 0 a 3 reintentos opcionales en sectores defectuosos; cada intento carga la unidad. Los ceros causan lagunas; la parada segura conserva el último punto de control.',
    '故障扇区可选择重试 0–3 次；每次重试都会增加磁盘负担。填零会产生数据缺口；安全停止会保留最后的检查点。',
    'По желанию 0–3 повтора для сбойных секторов; каждая попытка нагружает носитель. Нули создают пробелы; безопасная остановка сохраняет последнюю контрольную точку.',
    '不良セクターの再読み取りは0～3回。試行は媒体に負荷をかけます。ゼロ埋めは欠損を生み、安全停止は直前のチェックポイントを保持します。')

# Session persistence (Tenshi 2.6.0)
add('Analysesitzung', 'Analysis session', 'Sesión de análisis', '分析会话', 'Сеанс анализа', '解析セッション')
add('Sitzung speichern', 'Save session', 'Guardar sesión', '保存会话', 'Сохранить сеанс', 'セッションを保存')
add('Sitzung laden', 'Load session', 'Cargar sesión', '加载会话', 'Загрузить сеанс', 'セッションを読み込む')
add('Analysesitzung speichern', 'Save analysis session', 'Guardar sesión de análisis', '保存分析会话', 'Сохранить сеанс анализа', '解析セッションを保存')
add('Analysesitzung laden', 'Load analysis session', 'Cargar sesión de análisis', '加载分析会话', 'Загрузить сеанс анализа', '解析セッションを読み込む')
add('Sitzung und Quell-Image werden geprüft …', 'Checking session and source image …', 'Comprobando sesión e imagen de origen …', '正在验证会话和源镜像…', 'Проверка сеанса и исходного образа …', 'セッションと元のイメージを検証中…')
add('Analysesitzung wird gespeichert …', 'Saving analysis session …', 'Guardando sesión de análisis …', '正在保存分析会话…', 'Сохранение сеанса анализа …', '解析セッションを保存中…')
add('Analysesitzung gespeichert. Beim Laden wird das Image erneut geprüft.', 'Session saved. The image will be checked again when loaded.', 'Sesión guardada. La imagen se comprobará al cargarla.', '会话已保存。加载时将再次验证镜像。', 'Сеанс сохранён. При загрузке образ будет проверен заново.', 'セッションを保存しました。読み込み時にイメージを再検証します。')
add('Analysesitzung geladen und Image geprüft. Dateiinhalte bleiben ungeprüft.', 'Session loaded and image checked. File contents remain unverified.', 'Sesión cargada e imagen comprobada. No se ha verificado el contenido de los archivos.', '会话已加载且镜像已验证，文件内容尚未验证。', 'Сеанс загружен, образ проверен. Содержимое файлов не проверено.', 'セッションを読み込み、イメージを検証しました。ファイル内容は未検証です。')
add('Bitte laufende Vorgänge zuerst abschließen.', 'Please finish running operations first.', 'Finalice primero las operaciones en curso.', '请先完成正在运行的操作。', 'Сначала завершите выполняющиеся операции.', 'まず実行中の処理を完了してください。')
add('Ursprüngliches Image fehlt – identisches Image auswählen', 'Original image missing – select identical image', 'Falta la imagen original: seleccione una idéntica', '原始镜像缺失——请选择相同镜像', 'Исходный образ отсутствует — выберите идентичный', '元のイメージがありません。同一のイメージを選択してください')

# More precise recovery warnings (Tenshi 2.8.0)
add('NTFS-Datenstrom enthält überlappende physische Clusterbereiche.',
    'NTFS stream has overlapping physical cluster ranges.',
    'El flujo NTFS contiene rangos de clústeres físicos superpuestos.',
    'NTFS 数据流包含重叠的物理簇范围。',
    'Поток NTFS содержит пересекающиеся физические кластеры.',
    'NTFS データストリームに物理クラスタの重複があります。')
add('NTFS-Cluster der gelöschten Datei werden laut aktuellen MFT-Metadaten bereits von einer vorhandenen Datei genutzt. Der ursprüngliche Dateiinhalt ist an diesen Stellen nicht zuverlässig zuordenbar.',
    'Current MFT metadata shows that an existing file already uses clusters of the deleted file. The original contents cannot be reliably assigned at those locations.',
    'Los metadatos MFT actuales indican que un archivo existente ya usa clústeres del archivo borrado. El contenido original no puede atribuirse de forma fiable en esos sectores.',
    '当前 MFT 元数据显示，已存在的文件占用了被删除文件的簇。无法可靠确认这些位置的原始内容。',
    'Текущие метаданные MFT показывают, что кластеры удалённого файла заняты существующим файлом. Исходные данные в этих областях нельзя надёжно установить.',
    '現在の MFT メタデータでは、削除ファイルのクラスタが既存ファイルに使用されています。該当範囲の元データは確実に特定できません。')
add('Gelöscht: freie Cluster können bereits überschrieben sein.',
    'Deleted: previously allocated clusters may already have been overwritten.',
    'Eliminado: los clústeres pueden haberse sobrescrito.',
    '已删除：原簇可能已被覆盖。',
    'Удалено: кластеры могли быть перезаписаны.',
    '削除済み：クラスタは上書きされた可能性があります。')
add('Metadaten plausibel; Dateiinhalt bleibt ungeprüft.',
    'Metadata plausible; file contents remain unverified.',
    'Metadatos plausibles; el contenido sigue sin verificarse.',
    '元数据合理，但文件内容未经验证。',
    'Метаданные правдоподобны; содержимое не проверено.',
    'メタデータは妥当ですが、ファイル内容は未検証です。')
add('Gesperrt', 'Blocked', 'Bloqueado', '已阻止', 'Заблокировано', 'ブロック')
add('Warnung', 'Warning', 'Advertencia', '警告', 'Предупреждение', '警告')
add('Bereit', 'Ready', 'Listo', '就绪', 'Готово', '準備完了')
add('Ordner', 'Folder', 'Carpeta', '文件夹', 'Папка', 'フォルダー')

# Recovery preflight (Tenshi 2.3.0)
add('Export prüfen','Check export','Comprobar exportación','检查导出','Проверить экспорт','エクスポートを検査')
add('Export-Vorabprüfung','Export preflight','Comprobación previa','导出前检查','Предварительная проверка экспорта','エクスポート事前検査')
add('Tenshi – Export-Vorabprüfung','Tenshi – Export preflight','Tenshi – Comprobación previa','Tenshi – 导出前检查','Tenshi – Предварительная проверка','Tenshi – エクスポート事前検査')
add('Export-Vorabprüfung (ohne Dateiinhalte zu lesen)','Export preflight (without reading file contents)','Comprobación previa (sin leer los archivos)','导出前检查（不读取文件内容）','Предварительная проверка (без чтения содержимого)','エクスポート事前検査（内容は読み込まない）')
add('Prüfbericht speichern','Save check report','Guardar informe de comprobación','保存检查报告','Сохранить отчёт проверки','検査レポートを保存')
add('Bewertung','Assessment','Evaluación','评估','Оценка','評価')
add('Hinweise','Notes','Notas','提示','Примечания','注意事項')
add('Bitte Dateien oder Ordner in der rechten Liste markieren.','Select files or folders from the right-hand list.','Seleccione archivos o carpetas en la lista derecha.','请在右侧列表中选择文件或文件夹。','Выберите файлы или папки в списке справа.','右側の一覧でファイルかフォルダーを選んでください。')
add('Quelle wurde gewechselt. Ergebnis verworfen.','Source changed. Results discarded.','Cambió el origen. Se descartaron los resultados.','源已改变，结果已丢弃。','Источник изменился. Результат отброшен.','ソースが変更されたため結果を破棄しました。')
add('Bericht erfolgreich gespeichert.','Report saved.','Informe guardado.','报告已保存。','Отчёт сохранён.','レポートを保存しました。')


# Appearance controls (Tenshi 2.4.0)
add('Darstellung', 'Appearance', 'Apariencia', '外观', 'Оформление', '外観')
add('◐  Darstellung', '◐  Appearance', '◐  Apariencia', '◐  外观', '◐  Оформление', '◐  外観')
add('Hell', 'Light', 'Claro', '浅色', 'Светлая', 'ライト')
add('Dunkel', 'Dark', 'Oscuro', '深色', 'Тёмная', 'ダーク')
add('Hohe Plausibilität', 'High confidence', 'Alta confianza', '高可信度', 'Высокая достоверность', '確度が高い')
add('Mittlere Plausibilität', 'Medium confidence', 'Confianza media', '中等可信度', 'Средняя достоверность', '確度が中程度')
add('Geringe Plausibilität', 'Low confidence', 'Baja confianza', '低可信度', 'Низкая достоверность', '確度が低い')
add('Auffällige Partitionen', 'Flagged partitions', 'Particiones con avisos', '异常分区', 'Подозрительные разделы', '注意が必要なパーティション')

# Main window, sections and menus
add('Tenshi — Datenrettung', 'Tenshi — Data Recovery', 'Tenshi — Recuperación de datos', 'Tenshi — 数据恢复', 'Tenshi — Восстановление данных', 'Tenshi — データ復旧')
add('Datenrettung & schreibgeschützte Datenträgeranalyse', 'Data recovery & read-only disk analysis', 'Recuperación y análisis de discos de solo lectura', '数据恢复与只读磁盘分析', 'Восстановление данных и анализ дисков только для чтения', 'データ復旧と読み取り専用ディスク解析')
add('Partitionen · Dateien & Ordner', 'Partitions · Files & Folders', 'Particiones · Archivos y carpetas', '分区 · 文件与文件夹', 'Разделы · Файлы и папки', 'パーティション · ファイルとフォルダー')
add('▦  Partitionen', '▦  Partitions', '▦  Particiones', '▦  分区', '▦  Разделы', '▦  パーティション')
add('📁  Dateien & Ordner', '📁  Files & Folders', '📁  Archivos y carpetas', '📁  文件与文件夹', '📁  Файлы и папки', '📁  ファイルとフォルダー')
add('Partitionen', 'Partitions', 'Particiones', '分区', 'Разделы', 'パーティション')
add('Dateien & Ordner', 'Files & Folders', 'Archivos y carpetas', '文件与文件夹', 'Файлы и папки', 'ファイルとフォルダー')
add('Ausgewählte Quelle:', 'Selected source:', 'Origen seleccionado:', '所选来源：', 'Выбранный источник:', '選択したソース:')
add('Image auswählen', 'Select image', 'Seleccionar imagen', '选择镜像', 'Выбрать образ', 'イメージを選択')
add('Physischer Datenträger auswählen', 'Select physical disk', 'Seleccionar disco físico', '选择物理磁盘', 'Выбрать физический диск', '物理ディスクを選択')
add('Laufwerk auswählen', 'Select volume', 'Seleccionar unidad', '选择卷', 'Выбрать том', 'ドライブを選択')
add('Image erstellen / fortsetzen', 'Create / resume image', 'Crear / reanudar imagen', '创建／继续镜像', 'Создать / продолжить образ', 'イメージ作成／再開')
add('Bereit. Quelldatenträger werden nur lesend geöffnet.', 'Ready. Source disks are opened read-only.', 'Listo. Los discos de origen se abren en modo de solo lectura.', '就绪。源磁盘以只读方式打开。', 'Готово. Исходные диски открываются только для чтения.', '準備完了。ソースディスクは読み取り専用で開きます。')
add('Bei Hardwaredefekt weitere Lesezugriffe minimieren und möglichst ein schonendes Image erstellen. Gerettete Daten nur auf einem anderen physischen Datenträger speichern.',
    'If hardware may be failing, minimize further reads and create an image using a gentle recovery process. Save recovered data on a different physical drive.',
    'Si el hardware puede fallar, reduzca las lecturas y cree una imagen con un método cuidadoso. Guarde los datos recuperados en otra unidad física.',
    '如果硬件可能故障，请减少读取并采用谨慎方式制作镜像。将恢复的数据保存到另一块物理磁盘。',
    'При аппаратной неисправности ограничьте чтение и создайте образ щадящим способом. Сохраняйте восстановленные данные на другом физическом диске.',
    'ハードウェア故障が疑われる場合は追加の読み取りを抑え、安全性に配慮してイメージを作成してください。復旧データは別の物理ドライブに保存してください。')

add('Fehlerprotokoll', 'Error log', 'Registro de errores', '错误日志', 'Журнал ошибок', 'エラーログ')
add('Noch keine Fehler protokolliert.', 'No errors recorded yet.', 'Todavía no se han registrado errores.', '尚未记录错误。', 'Ошибки пока не записаны.', 'エラーはまだ記録されていません。')
add('Fehlerprotokoll kann nicht geöffnet werden.', 'The error log cannot be opened.', 'No se puede abrir el registro de errores.', '无法打开错误日志。', 'Не удаётся открыть журнал ошибок.', 'エラーログを開けません。')
add('Sprache', 'Language', 'Idioma', '语言', 'Язык', '言語')
add('Sprache auswählen', 'Choose language', 'Seleccionar idioma', '选择语言', 'Выбор языка', '言語を選択')
add('Doppelklick auf eine Partition: Dateisystem automatisch einlesen.',
    'Double-click a partition to load its file system automatically.',
    'Haga doble clic en una partición para cargar su sistema de archivos.',
    '双击分区可自动读取文件系统。',
    'Дважды щёлкните раздел, чтобы автоматически прочитать файловую систему.',
    'パーティションをダブルクリックするとファイルシステムを自動的に読み込みます。')
# Automatic read-only quick scan after source selection (Tenshi 3.0.2).
add('Quelle auswählen: Schnellanalyse startet automatisch.',
    'Select a source: a quick scan starts automatically.',
    'Seleccione un origen: el análisis rápido se iniciará automáticamente.',
    '选择数据源后将自动开始快速扫描。',
    'Выберите источник: быстрый анализ начнётся автоматически.',
    'ソースを選択するとクイックスキャンが自動で始まります。')
add('Neue Quelle ausgewählt. Schnellanalyse startet automatisch.',
    'New source selected. Quick scan starts automatically.',
    'Nuevo origen seleccionado. El análisis rápido comienza automáticamente.',
    '已选择新数据源。快速扫描即将自动开始。',
    'Выбран новый источник. Быстрый анализ запускается автоматически.',
    '新しいソースを選択しました。クイックスキャンを自動で開始します。')

# Partition analysis
add('Schnellanalyse (64 MiB)', 'Quick scan (64 MiB)', 'Análisis rápido (64 MiB)', '快速扫描（64 MiB）', 'Быстрый анализ (64 МиБ)', 'クイックスキャン (64 MiB)')
add('Tiefensuche starten', 'Start deep scan', 'Iniciar búsqueda profunda', '开始深度扫描', 'Начать глубокий поиск', '詳細スキャン開始')
add('Limit (MiB, 0 = alles):', 'Limit (MiB, 0 = all):', 'Límite (MiB, 0 = todo):', '限制（MiB，0＝全部）：', 'Лимит (МиБ, 0 = всё):', '上限 (MiB、0=すべて):')
add('Sektorgröße:', 'Sector size:', 'Tamaño del sector:', '扇区大小：', 'Размер сектора:', 'セクターサイズ:')
add('Ausgewählte Partition prüfen', 'Inspect selected partition', 'Examinar partición seleccionada', '检查所选分区', 'Проверить выбранный раздел', '選択したパーティションを検査')
add('Partitionsbericht speichern', 'Save partition report', 'Guardar informe de partición', '保存分区报告', 'Сохранить отчёт о разделе', 'パーティションレポートを保存')
add('Nur Metadatenprüfung – keine Reparatur oder Vollprüfung', 'Metadata check only — no repair or full verification', 'Solo metadatos; no repara ni comprueba todo', '仅检查元数据，不进行修复或完整检查', 'Только проверка метаданных — без исправления', 'メタデータ確認のみ。修復や完全検査ではありません')
add('Speicherbelegung: unbekannt – Partition auswählen und prüfen.', 'Space usage: unknown — select and inspect a partition.', 'Espacio usado: desconocido; seleccione una partición.', '空间使用情况：未知，请选择并检查分区。', 'Использование: неизвестно — выберите и проверьте раздел.', '使用容量: 不明。パーティションを選択して検査してください。')
add('Speicherbelegung: unbekannt (keine vollständigen Metadaten).', 'Space usage: unknown (incomplete metadata).', 'Espacio usado: desconocido (metadatos incompletos).', '空间使用情况：未知（元数据不完整）。', 'Использование: неизвестно (неполные метаданные).', '使用容量: 不明 (メタデータが不完全)。')
add('Image auswählen und Schnellanalyse starten.', 'Select an image and start a quick scan.', 'Seleccione una imagen e inicie el análisis rápido.', '选择镜像并开始快速扫描。', 'Выберите образ и запустите быстрый анализ.', 'イメージを選択しクイックスキャンを開始してください。')
add('Gefundene Bootsektoren ohne Partitionstabelle sind Kandidaten, keine bestätigten Partitionen.', 'Boot sectors found without a partition table are candidates, not confirmed partitions.', 'Los sectores de arranque sin tabla son candidatos, no particiones confirmadas.', '未找到分区表时检测到的引导扇区仅为候选，不是已确认分区。', 'Найденные без таблицы разделов загрузочные секторы — лишь кандидаты.', 'パーティションテーブルなしで見つかったブートセクターは候補であり、確定ではありません。')
add('Fundliste speichern', 'Save findings list', 'Guardar hallazgos', '保存分区发现', 'Сохранить найденные разделы', '検出結果を保存')
add('Partition auswählen und „Ausgewählte Partition prüfen“ anklicken.', 'Select a partition and click “Inspect selected partition”.', 'Seleccione una partición y pulse «Examinar partición seleccionada».', '选择分区并点击“检查所选分区”。', 'Выберите раздел и нажмите «Проверить выбранный раздел».', 'パーティションを選択し「選択したパーティションを検査」を押してください。')
for vals in [
('Nr.','No.','N.º','编号','№','番号'),('Erkennung','Detected by','Detección','检测方式','Обнаружение','検出方法'),
('Byte-Offset','Byte offset','Desplazamiento','字节偏移','Смещение, байт','バイトオフセット'),('Größe','Size','Tamaño','大小','Размер','サイズ'),
('Dateisystem','File system','Sistema de archivos','文件系统','Файловая система','ファイルシステム'),
('Belegt*','Used*','Usado*','已用*','Занято*','使用済*'),('Struktur','Structure','Estructura','结构','Структура','構造'),
('Sektor','Sector','Sector','扇区','Сектор','セクター'),('Typ/GUID','Type/GUID','Tipo/GUID','类型/GUID','Тип/GUID','種類/GUID'),
('Plausibilität','Plausibility','Plausibilidad','可信度','Достоверность','信頼度'),
('Hoch','High','Alta','高','Высокая','高'),
('Mittel','Medium','Media','中','Средняя','中'),
('Niedrig','Low','Baja','低','Низкая','低'),
('Ungeprüft','Unchecked','Sin comprobar','未检查','Не проверено','未確認'),
('Name','Name','Nombre','名称','Имя','名前'),('Nicht geprüft','Not checked','Sin comprobar','未检查','Не проверено','未検査'),
('Nicht zugeordnet','Unassigned','Sin asignar','未分配','Не распределено','未割り当て'),
('Status','Status','Estado','状态','Статус','状態'),('Rettbarkeit','Recoverability','Recuperabilidad','可恢复性','Возможность восстановления','復旧可能性'),
('Eintrags-ID','Entry ID','ID de entrada','条目 ID','ID записи','エントリー ID'),('Endung','Extension','Extensión','扩展名','Расширение','拡張子'),
('Geändert (UTC)','Modified (UTC)','Modificado (UTC)','修改时间（UTC）','Изменён (UTC)','更新日時 (UTC)'),('Pfad','Path','Ruta','路径','Путь','パス'),
('Typ','Type','Tipo','类型','Тип','種類'),('Datei / Ordner','File / Folder','Archivo / carpeta','文件／文件夹','Файл / папка','ファイル／フォルダー'),
('Ergebnis / Fehler','Result / Error','Resultado / error','结果／错误','Результат / ошибка','結果／エラー'),
('Laufwerk','Volume','Unidad','卷','Том','ドライブ'),('Laufwerke','Volumes','Unidades','卷','Тома','ドライブ'),
('Physischer Datenträger','Physical disk','Disco físico','物理磁盘','Физический диск','物理ディスク'),
('Größe (GiB)','Size (GiB)','Tamaño (GiB)','大小（GiB）','Размер (ГиБ)','サイズ (GiB)'),
('Frei (GiB)','Free (GiB)','Libre (GiB)','可用（GiB）','Свободно (ГиБ)','空き (GiB)'),
]: add(*vals)
# Paging controls for very large file lists (Tenshi 2.2.0)
add('◀ Vorherige Seite', '◀ Previous page', '◀ Página anterior', '◀ 上一页', '◀ Предыдущая страница', '◀ 前のページ')
add('Nächste Seite ▶', 'Next page ▶', 'Página siguiente ▶', '下一页 ▶', 'Следующая страница ▶', '次のページ ▶')
# File browser and searching
add('Partitionsoffset (Byte):','Partition offset (bytes):','Desplazamiento de partición (bytes):','分区偏移（字节）：','Смещение раздела (байт):','パーティションオフセット (バイト):')
add('Partition übernehmen','Use partition','Usar partición','使用该分区','Использовать раздел','パーティションを使用')
add('MFT-Limit (0=alle):','MFT limit (0=all):','Límite MFT (0=todos):','MFT 限制（0＝全部）：','Лимит MFT (0=все):','MFT上限 (0=すべて):')
add('Dateisystem einlesen','Read file system','Leer sistema de archivos','读取文件系统','Прочитать файловую систему','ファイルシステムを読み取る')
add('Scan abbrechen','Cancel scan','Cancelar análisis','取消扫描','Отменить анализ','スキャン中止')
add('Diagnose…','Diagnostics…','Diagnóstico…','诊断…','Диагностика…','診断…')
add('Fehlertolerante Suche (nur Images)','Fault-tolerant scan (images only)','Análisis tolerante a fallos (solo imágenes)','容错扫描（仅镜像）','Поиск с пропуском ошибок (только образы)','エラー許容スキャン (イメージのみ)')
add('Analysebericht speichern','Save analysis report','Guardar informe del análisis','保存分析报告','Сохранить отчёт анализа','解析レポートを保存')
add('Gelöschte Einträge anzeigen','Show deleted entries','Mostrar elementos eliminados','显示已删除条目','Показать удалённые записи','削除済み項目を表示')
add('Stapel-Export / fortsetzen','Batch export / resume','Exportación por lotes / reanudar','批量导出／继续','Пакетный экспорт / продолжить','一括エクスポート／再開')
add('Vorschau','Preview','Vista previa','预览','Предпросмотр','プレビュー')
add('Datei prüfen','Verify file','Verificar archivo','检查文件','Проверить файл','ファイルを検査')
add('Suche (alle Dateinamen):','Search (all filenames):','Buscar (todos los nombres):','搜索（所有文件名）：','Поиск (все имена файлов):','検索 (すべてのファイル名):')
add('Suchen','Search','Buscar','搜索','Поиск','検索')
add('Erweiterte Suche…','Advanced search…','Búsqueda avanzada…','高级搜索…','Расширенный поиск…','詳細検索…')
add('Zurück zum Ordner','Back to folder','Volver a la carpeta','返回文件夹','Вернуться к папке','フォルダーに戻る')
add('Rettbarkeitsfilter:','Recoverability filter:','Filtro de recuperación:','可恢复性筛选：','Фильтр восстановления:','復旧可能性フィルター:')
add('TMP anzeigen (nur Ansicht)','Show TMP (view only)','Mostrar TMP (solo vista)','显示 TMP（仅界面）','Показать TMP (только вид)','TMPを表示 (表示のみ)')
add('TMP-Einträge sind nur ausgeblendet; beim Export ganzer Ordner können sie enthalten sein.',
    'TMP entries are hidden only; exporting a whole folder may still include them.',
    'Las entradas TMP solo están ocultas; al exportar carpetas completas podrían incluirse.',
    'TMP 条目仅被隐藏；导出整个文件夹时可能仍会包含。',
    'Записи TMP лишь скрыты; при экспорте папки целиком они могут войти в результат.',
    'TMP項目は非表示になるだけです。フォルダー全体の書き出しには含まれる場合があります。')
add('Ordnerstruktur','Folder tree','Árbol de carpetas','文件夹树','Дерево папок','フォルダーツリー')
add('Dateien und Unterordner','Files and subfolders','Archivos y subcarpetas','文件及子文件夹','Файлы и подпапки','ファイルとサブフォルダー')
add('⚠ = Metadaten-Hinweis; kein Nachweis beschädigter Inhalte.','⚠ = Metadata warning; not proof of corrupted contents.','⚠ = Aviso de metadatos; no confirma daños en los archivos.','⚠＝元数据警告，不代表内容已损坏。','⚠ = Предупреждение о метаданных, не о содержимом.','⚠＝メタデータに関する警告。内容の破損は未確認。')
add('Noch kein Dateisystem eingelesen.','No file system loaded yet.','Aún no se ha leído un sistema de archivos.','尚未加载文件系统。','Файловая система ещё не прочитана.','ファイルシステムはまだ読み込まれていません。')
add('Wiederherstellungswarteschlange','Recovery queue','Cola de recuperación','恢复队列','Очередь восстановления','復旧キュー')
add('Dateistatus anzeigen','Show file status','Mostrar estado de archivos','显示文件状态','Показать состояние файлов','ファイル状態を表示')
add('Dateistatus ausblenden','Hide file status','Ocultar estado de archivos','隐藏文件状态','Скрыть состояние файлов','ファイル状態を非表示')
add('Ergebnisbericht','Results report','Informe de resultados','结果报告','Отчёт о результатах','結果レポート')
add('Erweiterte Dateisuche','Advanced file search','Búsqueda avanzada de archivos','高级文件搜索','Расширенный поиск файлов','詳細ファイル検索')
add('Dateiendungen (z. B. pdf, .docx, *.jpg; mehrere mit Komma)','Extensions (e.g. pdf, .docx, *.jpg; separate with commas)','Extensiones (p. ej., pdf, .docx, *.jpg; separadas por comas)','扩展名（如 pdf、.docx、*.jpg；多个用逗号分隔）','Расширения (например, pdf, .docx, *.jpg; через запятую)','拡張子 (例: pdf、.docx、*.jpg。複数はカンマ区切り)')
add('Dateitypen hinzufügen:','Add file types:','Agregar tipos de archivo:','添加文件类型：','Добавить типы файлов:','ファイル形式を追加:')
add('Bilder','Images','Imágenes','图片','Изображения','画像')
add('Videos','Videos','Vídeos','视频','Видео','動画')
add('Audio','Audio','Audio','音频','Аудио','音声')
add('Dokumente','Documents','Documentos','文档','Документы','文書')
add('Archive','Archives','Archivos comprimidos','压缩包','Архивы','アーカイブ')
add('Mehrere Kategorien kombinierbar · bestehende Endungen bleiben erhalten','Combine categories · existing extensions are preserved','Combine categorías · se mantienen las extensiones existentes','可组合多个类别 · 保留已有扩展名','Можно сочетать категории · текущие расширения сохраняются','カテゴリを組み合わせ可能 · 既存の拡張子は保持')
add('Min. MiB:','Min. MiB:','Mín. MiB:','最小 MiB：','Мин. МиБ:','最小 MiB:')
add('Max. MiB:','Max. MiB:','Máx. MiB:','最大 MiB：','Макс. МиБ:','最大 MiB:')
add('Eintragstyp','Entry type','Tipo de elemento','条目类型','Тип элемента','項目の種類')
add('Alle','All','Todos','全部','Все','すべて')
add('Nur Dateien','Files only','Solo archivos','仅文件','Только файлы','ファイルのみ')
add('Nur Ordner','Folders only','Solo carpetas','仅文件夹','Только папки','フォルダーのみ')
add('Dateinamen und ursprünglichen Ordnerpfad durchsuchen','Search filenames and original folder paths','Buscar nombres y rutas originales de carpetas','搜索文件名和原始文件夹路径','Поиск по именам и исходным путям','ファイル名と元のフォルダーパスを検索')
add('Zurücksetzen','Reset','Restablecer','重置','Сбросить','リセット')
add('Alle Einträge','All entries','Todos los elementos','所有条目','Все записи','すべての項目')
add('Auffällige Einträge','Flagged entries','Elementos con avisos','异常条目','Проблемные записи','注意が必要な項目')
add('Export möglich','Export possible','Exportación posible','可导出','Экспорт возможен','エクスポート可能')
add('Gelöscht / unsicher','Deleted / uncertain','Eliminados / inciertos','已删除／不确定','Удалено / ненадёжно','削除済み／不確実')
add('Eingeschränkt','Limited','Limitado','受限','Ограничено','制限あり')
add('Nicht exportierbar','Cannot export','No exportable','无法导出','Нельзя экспортировать','エクスポート不可')
add('Nur Namenshinweise','Name hints only','Solo nombres recuperados','仅名称线索','Только подсказки имён','名前の手掛かりのみ')
add('Ordner öffnen','Open folder','Abrir carpeta','打开文件夹','Открыть папку','フォルダーを開く')
add('Pfad kopieren','Copy path','Copiar ruta','复制路径','Копировать путь','パスをコピー')
add('Scan-Einstellungen und Diagnose','Scan settings and diagnostics','Opciones de análisis y diagnóstico','扫描设置与诊断','Настройки анализа и диагностика','スキャン設定と診断')
# Generic dialogs, imaging, verification
add('Schließen','Close','Cerrar','关闭','Закрыть','閉じる')
add('Abbrechen','Cancel','Cancelar','取消','Отмена','キャンセル')
add('Auswahl übernehmen (nur lesen)','Confirm selection (read-only)','Confirmar selección (solo lectura)','确认选择（只读）','Подтвердить (только чтение)','選択を確定 (読み取り専用)')
add('Auswahl fehlt','No selection','Falta selección','未选择','Ничего не выбрано','未選択')
add('Laufwerk auswählen – nur lesen','Select volume — read-only','Seleccionar unidad — solo lectura','选择卷 — 只读','Выбор тома — только чтение','ドライブ選択 — 読み取り専用')
add('Physischen Datenträger auswählen – nur lesen','Select physical disk — read-only','Seleccionar disco físico — solo lectura','选择物理磁盘 — 只读','Выбор диска — только чтение','物理ディスクを選択 — 読み取り専用')
add('Quelle (nur lesen):','Source (read-only):','Origen (solo lectura):','源（只读）：','Источник (только чтение):','ソース (読み取り専用):')
add('Ziel-Image:','Destination image:','Imagen de destino:','目标镜像：','Образ назначения:','保存先イメージ:')
add('Durchsuchen …','Browse…','Examinar…','浏览…','Обзор…','参照…')
add('Blockgröße:','Block size:','Tamaño de bloque:','块大小：','Размер блока:','ブロックサイズ:')
add('Unterbrechen','Pause','Pausar','暂停','Приостановить','一時停止')
add('Image erstellen','Create image','Crear imagen','创建镜像','Создать образ','イメージ作成')
add('Noch nicht gestartet.','Not started yet.','Aún no iniciado.','尚未开始。','Ещё не начато.','未開始。')
add('Dateivorschau – ','File preview — ','Vista previa — ','文件预览 — ','Предпросмотр — ','ファイルプレビュー — ')
add('Dateiprüfung – ','File verification — ','Verificación — ','文件检查 — ','Проверка файла — ','ファイル検査 — ')
add('Datei vor der Wiederherstellung prüfen','Verify file before recovery','Verificar archivo antes de recuperar','恢复前检查文件','Проверить файл до восстановления','復旧前にファイルを検査')
add('Vollständig lesend prüfen','Verify full readability','Comprobar lectura completa','检查完整可读性','Проверить полную читаемость','全体を読み取り検査')
add('Prüfung abbrechen','Cancel verification','Cancelar verificación','取消检查','Прервать проверку','検査を中止')
add('Tenshi – Image erstellen / fortsetzen','Tenshi – Create / resume image','Tenshi – Crear / reanudar imagen','Tenshi – 创建／继续镜像','Tenshi – Создать / продолжить образ','Tenshi – イメージ作成／再開')
add('Tenshi – Exportergebnisse','Tenshi – Export results','Tenshi – Resultados de exportación','Tenshi – 导出结果','Tenshi – Результаты экспорта','Tenshi – エクスポート結果')
add('Erweiterte Suche','Advanced search','Búsqueda avanzada','高级搜索','Расширенный поиск','詳細検索')
add('Partitionsanalyse','Partition analysis','Análisis de particiones','分区分析','Анализ разделов','パーティション解析')
add('Partitionsprüfung','Partition inspection','Inspección de partición','分区检查','Проверка раздела','パーティション検査')
add('Partitionsbericht','Partition report','Informe de partición','分区报告','Отчёт о разделе','パーティションレポート')
add('Analysebericht','Analysis report','Informe de análisis','分析报告','Отчёт об анализе','解析レポート')
add('Export','Export','Exportar','导出','Экспорт','エクスポート')
add('Stapel-Export','Batch export','Exportación por lotes','批量导出','Пакетный экспорт','一括エクスポート')
add('Sicherer Export','Safe export','Exportación segura','安全导出','Безопасный экспорт','安全なエクスポート')
add('Dateiprüfung','File verification','Verificación de archivos','文件检查','Проверка файла','ファイル検査')
add('Einzelergebnis','Item result','Resultado individual','单项结果','Результат элемента','項目の結果')
add('NTFS-Ordneransicht','NTFS folder view','Carpetas NTFS','NTFS 文件夹视图','Папки NTFS','NTFSフォルダー表示')
add('NTFS-Analyse unvollständig','NTFS analysis incomplete','Análisis NTFS incompleto','NTFS 分析未完成','Анализ NTFS неполон','NTFS解析が不完全です')
add('Dateisystem nur teilweise gelesen','File system partially read','Sistema de archivos leído parcialmente','文件系统读取不完整','Файловая система прочитана частично','ファイルシステムを一部のみ読み取り')
add('Dateisystem', 'File system', 'Sistema de archivos', '文件系统', 'Файловая система', 'ファイルシステム')
add('Suche', 'Search', 'Búsqueda', '搜索', 'Поиск', '検索')
add('Partition', 'Partition', 'Partición', '分区', 'Раздел', 'パーティション')
add('Vorschau fehlgeschlagen: ', 'Preview failed: ', 'Falló la vista previa: ', '预览失败：', 'Ошибка предпросмотра: ', 'プレビューに失敗: ')
add('Bildvorschau (Originalgröße, ggf. abgeschnitten)','Image preview (original size, possibly clipped)','Vista previa de imagen (tamaño original, quizá recortada)','图片预览（原始大小，可能被裁剪）','Просмотр изображения (оригинальный размер, может обрезаться)','画像プレビュー (元のサイズ、切り取られる場合あり)')
# Safeguards; these contain no filenames and may appear in dialogs
add('Bitte zuerst ein Laufwerk markieren.','Select a volume first.','Seleccione primero una unidad.','请先选择一个卷。','Сначала выберите том.','先にドライブを選択してください。')
add('Bitte eine Partition markieren.','Select a partition.','Seleccione una partición.','请选择一个分区。','Выберите раздел.','パーティションを選択してください。')
add('Bitte genau eine Datei auswählen.','Select exactly one file.','Seleccione exactamente un archivo.','请选择一个文件。','Выберите ровно один файл.','ファイルを1つだけ選択してください。')
add('Zuerst ein Dateisystem einlesen.','Read a file system first.','Lea primero un sistema de archivos.','请先读取文件系统。','Сначала прочитайте файловую систему.','先にファイルシステムを読み込んでください。')
add('Bericht erfolgreich gespeichert.','Report saved successfully.','Informe guardado correctamente.','报告已保存。','Отчёт успешно сохранён.','レポートを保存しました。')
add('Prüfung läuft', 'Verifying', 'Verificando', '正在检查', 'Проверка', '検査中')
add('Fehler', 'Error', 'Error', '错误', 'Ошибка', 'エラー')
add('Abbruch', 'Cancelled', 'Cancelado', '已取消', 'Отменено', 'キャンセル')
add('Keine zusätzlichen Hinweise.', 'No additional notes.', 'Sin observaciones adicionales.', '没有其他提示。', 'Дополнительных замечаний нет.', '追加の注意事項はありません。')

# Common dynamic German fragments, only on UI output, never on disk data.
_FRAGMENTS = [
    ('Gesamtgröße:', 'Total size:', 'Tamaño total:', '总大小：', 'Общий размер:', '合計サイズ:'),
    ('Ausgewählt:', 'Selected:', 'Seleccionado:', '已选择：', 'Выбрано:', '選択済み:'),
    ('Dateigröße:', 'File size:', 'Tamaño del archivo:', '文件大小：', 'Размер файла:', 'ファイルサイズ:'),
    ('Dateisystemsuche:', 'File system scan:', 'Análisis del sistema:', '文件系统扫描：', 'Поиск файловой системы:', 'ファイルシステム検索:'),
    ('Partitionsanalyse abgeschlossen:', 'Partition scan complete:', 'Análisis de particiones finalizado:', '分区扫描完成：', 'Анализ разделов завершён:', 'パーティション解析が完了:'),
    ('Nicht lesbar:', 'Unreadable:', 'Ilegible:', '不可读取：', 'Не читается:', '読み取り不可:'),
    ('nicht lesbar:', 'unreadable:', 'ilegible:', '不可读取：', 'не читается:', '読み取り不可:'),
    ('Restzeit', 'remaining', 'restante', '剩余时间', 'осталось', '残り時間'),
    ('Einträge', 'entries', 'elementos', '条目', 'записей', '項目'),
    ('gefunden', 'found', 'encontrados', '已找到', 'найдено', '検出'),
    ('gelesen', 'read', 'leído', '已读取', 'прочитано', '読み取り済み'),
    ('Speicherbelegung:', 'Space usage:', 'Uso de espacio:', '空间使用：', 'Использование места:', '使用容量:'),
    ('Bereich/e', 'range(s)', 'rango(s)', '区域', 'диапазон(ы)', '範囲'),
    ('Wiederherstellung', 'Recovery', 'Recuperación', '恢复', 'Восстановление', '復旧'),
    ('abgeschlossen', 'completed', 'finalizado', '已完成', 'завершено', '完了'),
]
for row in _FRAGMENTS:
    if row[0] not in TRANSLATIONS:
        add(*row)

# Text is translated only if it is an actual UI phrase, or contains a
# multi-character German phrase known in the catalog. Never perform word-level
# replacements in arbitrary paths, filenames or hexdumps.
_PARTIAL = [s for s in TRANSLATIONS if len(s) >= 9 and (s.endswith(':') or s.endswith(' ') or s in {'Tenshi — Datenrettung', 'Restzeit', 'Einträge', 'gefunden', 'gelesen', 'abgeschlossen'})]
_PARTIAL.sort(key=len, reverse=True)

def translate(text: str, language: str = 'de') -> str:
    if language == 'de' or not text or not isinstance(text, str):
        return text
    match = TRANSLATIONS.get(text)
    if match:
        return match.get(language, text)
    if '\n' in text:
        return '\n'.join(translate(line, language) for line in text.split('\n'))
    # A display-only status string with embedded numbers, not a file path.
    if ('\\' in text or '/' in text or '\x00' in text) and not text.startswith('Tenshi'):
        return text
    result = text
    for source in _PARTIAL:
        if source in result:
            result = result.replace(source, TRANSLATIONS[source].get(language, source))
    return result


def canonical_choice(value: str, options: tuple[str, ...], lang: str) -> str:
    """Map a translated dropdown choice back to its original internal key."""
    for option in options:
        if value == option or value == translate(option, lang):
            return option
    return options[0]


def settings_path() -> Path:
    override = os.environ.get('TENSHI_SETTINGS_FILE')
    if override:
        return Path(override)
    root = os.environ.get('APPDATA') or os.environ.get('XDG_CONFIG_HOME')
    if root:
        return Path(root) / 'Tenshi' / 'settings.json'
    return Path.home() / '.config' / 'Tenshi' / 'settings.json'


def load_language() -> str:
    try:
        loaded = json.loads(settings_path().read_text(encoding='utf-8'))
        language = loaded.get('language', 'de')
        return language if language in LANGUAGES else 'de'
    except (OSError, ValueError, TypeError, AttributeError):
        return 'de'


def save_language(language: str) -> None:
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    dest = settings_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    # No dependence on current working directory or a recovery source device.
    fd, staging = tempfile.mkstemp(prefix='tenshi-settings-', suffix='.tmp', dir=str(dest.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            try:
                existing = json.loads(dest.read_text(encoding='utf-8'))
                if not isinstance(existing, dict):
                    existing = {}
            except (OSError, ValueError, TypeError):
                existing = {}
            existing['language'] = language
            json.dump(existing, out, ensure_ascii=False, indent=2)
        os.replace(staging, dest)
    finally:
        try:
            os.unlink(staging)
        except FileNotFoundError:
            pass


class DialogProxy:
    """Translate native messagebox and file dialog copy without changing data."""
    def __init__(self, wrapped, get_language, is_file_dialog=False):
        self.wrapped = wrapped
        self.get_language = get_language
        self.is_file_dialog = is_file_dialog

    def __getattr__(self, name):
        original = getattr(self.wrapped, name)
        if not callable(original):
            return original
        def call(*args, **kwargs):
            if self.is_file_dialog:
                parent=kwargs.get('parent') or getattr(tk,'_default_root',None)
                if not isinstance(parent,tk.Misc):parent=getattr(tk,'_default_root',None)
                if parent is not None:
                    colors=getattr(parent._root(),'_file_dialog_colors',None)
                    if colors is not None:colors.prepare()
            lang = self.get_language()
            mapped_args = list(args)
            if name in ('showerror', 'showinfo', 'showwarning', 'askyesno', 'askokcancel', 'askquestion', 'askretrycancel', 'askyesnocancel'):
                mapped_args = [translate(item, lang) if isinstance(item, str) else item for item in mapped_args]
            for key in ('title', 'message', 'detail'):
                if key in kwargs:
                    kwargs[key] = translate(kwargs[key], lang)
            if 'filetypes' in kwargs:
                kwargs['filetypes'] = [(translate(label, lang), pattern) for label, pattern in kwargs['filetypes']]
            return original(*mapped_args, **kwargs)
        return call


class UITranslator:
    """Update current and future Tk widgets while retaining canonical text."""
    def __init__(self, root: tk.Tk, language='de'):
        self.root = root
        self.language = language if language in LANGUAGES else 'de'
        self.widget_data = {}
        self.var_data = {}
        self._in_var_change = False
        self._after_id = None

    def set_language(self, language: str):
        if language not in LANGUAGES:
            raise ValueError('Unknown language')
        self.language = language
        self.refresh()

    def start(self):
        self.refresh()
        self._schedule()

    def stop(self):
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _schedule(self):
        try:
            if self.root.winfo_exists():
                self._after_id = self.root.after(320, self._pulse)
        except tk.TclError:
            return

    def _pulse(self):
        self._after_id = None
        try:
            if self.root.winfo_exists():
                self.refresh()
                self._schedule()
        except tk.TclError:
            pass

    def _walk(self, widget):
        yield widget
        try:
            children = widget.winfo_children()
        except tk.TclError:
            return
        for child in children:
            yield from self._walk(child)

    def _capture_text(self, widget, key, current, apply):
        ident = (widget, key)
        stored = self.widget_data.get(ident)
        if stored is None or current not in (stored[0], stored[1]):
            stored = (current, current)
        base = stored[0]
        wanted = translate(base, self.language)
        if current != wanted:
            try:
                apply(wanted)
            except tk.TclError:
                pass
        self.widget_data[ident] = (base, wanted)

    def _bind_var(self, var_name):
        if not var_name or var_name in self.var_data:
            return
        var = tk.StringVar(master=self.root, name=var_name)
        source = var.get()
        row = {'var':var, 'source':source, 'last':source}
        self.var_data[var_name] = row
        def on_write(*args):
            if self._in_var_change:
                return
            new = var.get()
            if new != row['last']:
                row['source'] = new
            self._apply_var(row)
        var.trace_add('write', on_write)
        row['trace'] = on_write

    def _apply_var(self, row):
        value = translate(row['source'], self.language)
        row['last'] = value
        try:
            current = row['var'].get()
        except tk.TclError:
            # Dialog-local StringVars may be unset when their window closes.
            self.var_data.pop(str(row['var']), None)
            return
        if current != value:
            self._in_var_change = True
            try:
                row['var'].set(value)
            finally:
                self._in_var_change = False

    def refresh(self):
        for widget in self._walk(self.root):
            try:
                if isinstance(widget, (tk.Tk, tk.Toplevel)):
                    self._capture_text(widget, 'title', widget.title(), widget.title)
                options = widget.keys() if hasattr(widget, 'keys') else ()
                if 'text' in options:
                    value = widget.cget('text')
                    self._capture_text(widget, 'text', value,
                                       lambda t, w=widget: w.configure(text=t))
                if 'textvariable' in options and isinstance(widget, (tk.Label, ttk.Label)):
                    self._bind_var(widget.cget('textvariable'))
                if isinstance(widget, ttk.Treeview):
                    for column in ('#0',) + tuple(widget['columns']):
                        heading = widget.heading(column)['text']
                        self._capture_text(widget, f'heading:{column}', heading,
                                           lambda t, w=widget, c=column: w.heading(c, text=t))
                if isinstance(widget, tk.Text) and widget in (
                    getattr(self.root, 'partition_detail_text', None),
                    getattr(self.root, 'partition_warnings', None)):
                    contents = widget.get('1.0', 'end-1c')
                    def apply_text(value, w=widget):
                        old_state = str(w.cget('state'))
                        w.configure(state='normal')
                        try:
                            w.delete('1.0', 'end')
                            w.insert('1.0', value)
                        finally:
                            w.configure(state=old_state)
                    self._capture_text(widget, 'read_only_text', contents, apply_text)
                if isinstance(widget, tk.Menu):
                    end = widget.index('end')
                    if end is not None:
                        for index in range(end+1):
                            if widget.type(index) not in ('command', 'cascade', 'checkbutton', 'radiobutton'):
                                continue
                            label = widget.entrycget(index, 'label')
                            self._capture_text(widget, f'menu:{index}', label,
                                               lambda t, w=widget, i=index: w.entryconfigure(i, label=t))
            except (tk.TclError, ValueError):
                continue
        for row in list(self.var_data.values()):
            self._apply_var(row)

# Descriptions and safety notices shown in the main file browser and scan dialog.
add('NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  Partitionen · Dateien & Ordner',
    'NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  Partitions · Files & Folders',
    'NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  Particiones · Archivos y carpetas',
    'NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  分区 · 文件与文件夹',
    'NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  Разделы · Файлы и папки',
    'NTFS · FAT32 · exFAT · ext2/3/4 · Btrfs · XFS  |  パーティション · ファイルとフォルダー')
add('Dateiansicht: NTFS, FAT32, exFAT, ext2/3/4 sowie eingeschränkt Btrfs und XFS. Gelöschte Dateien: NTFS, FAT32, exFAT und ext2/3/4 teilweise rettbar; Btrfs/XFS nur nicht exportierbare Metadatenhinweise. Ein Export garantiert keine intakten Inhalte.',
    'File browser: NTFS, FAT32, exFAT, ext2/3/4, with limited Btrfs/XFS support. Deleted files: partial recovery for NTFS, FAT32, exFAT and ext2/3/4; Btrfs/XFS provide non-exportable metadata hints only. An export does not guarantee intact contents.',
    'Explorador: NTFS, FAT32, exFAT, ext2/3/4 y Btrfs/XFS con limitaciones. Borrados: recuperación parcial en NTFS, FAT32, exFAT y ext2/3/4; Btrfs/XFS solo muestran pistas de metadatos no exportables. La exportación no garantiza archivos íntegros.',
    '文件浏览：NTFS、FAT32、exFAT、ext2/3/4；Btrfs/XFS 功能有限。已删除文件：前四类文件系统可部分恢复，Btrfs/XFS 仅提供无法导出的元数据线索。导出并不保证内容完好。',
    'Просмотр: NTFS, FAT32, exFAT, ext2/3/4, ограниченная поддержка Btrfs/XFS. Удалённые файлы: частичное восстановление на NTFS, FAT32, exFAT, ext2/3/4; для Btrfs/XFS — только неэкспортируемые метаданные. Экспорт не гарантирует целостность.',
    'ファイル表示：NTFS、FAT32、exFAT、ext2/3/4、制限付きの Btrfs/XFS に対応。削除済みファイルは NTFS/FAT32/exFAT/ext2/3/4 で一部復旧可能。Btrfs/XFS は書き出せないメタデータの手掛かりのみ。エクスポートしても内容の完全性は保証されません。')

add('Noch kein Stapel-Export gestartet.','No batch export started.','Aún no se inició ninguna exportación.', '尚未开始批量导出。','Пакетный экспорт ещё не запущен.','一括エクスポートは未開始です。')
add('Überspringt unlesbare Datensätze/Unterordner. Die Ergebnisse können unvollständig bleiben.',
    'Skips unreadable records and subfolders. Results may be incomplete.',
    'Omite registros y subcarpetas ilegibles. Los resultados pueden ser incompletos.',
    '跳过无法读取的记录和子文件夹，结果可能不完整。',
    'Пропускает нечитаемые записи и подпапки. Результаты могут быть неполными.',
    '読み取れないレコードやサブフォルダーをスキップします。結果は不完全な場合があります。')
add('Überspringt unlesbare NTFS-Datensätze bzw. Unterordner; Ergebnis kann unvollständig sein.',
    'Skips unreadable NTFS records and subfolders; the result may be incomplete.',
    'Omite registros NTFS y subcarpetas ilegibles; los resultados pueden ser incompletos.',
    '跳过无法读取的 NTFS 记录及子文件夹，结果可能不完整。',
    'Пропускает нечитаемые записи NTFS и подпапки; результат может быть неполным.',
    '読み取れないNTFSレコードとサブフォルダーを飛ばします。結果は不完全な場合があります。')
add('Schreibzugriffe erfolgen nur auf die Image-Zieldatei (neu oder fortgesetzt) und ihre Statusdateien, nicht auf das Quellmedium. Für mechanisch defekte Laufwerke spezialisierte, schonende Imaging-Verfahren verwenden.',
    'Writes affect only the destination image (new or resumed) and its checkpoint files, never the source. For physically failing drives use specialist low-impact imaging.',
    'Solo se escriben la imagen de destino (nueva o reanudada) y sus estados, nunca el origen. Para discos defectuosos use métodos de imagen especializados.',
    '仅向目标镜像（新建或续传）及其状态文件写入，不写入源介质。对物理故障硬盘应使用专业的低负载镜像工具。',
    'Запись идёт только в целевой образ (новый или продолжаемый) и файлы состояния, но не в источник. Для неисправных дисков используйте специализированные щадящие средства.',
    '書き込み先は保存先イメージ（新規・再開）と状態ファイルのみで、元の媒体には書き込みません。物理的な故障時は専門的な低負荷イメージ作成手段を使用してください。')
add('Unlesbare Bereiche werden mit Nullen ersetzt und als Fehlstellen protokolliert; das Image kann dadurch Datenlücken enthalten.',
    'Unreadable areas are filled with zeros and logged; the image may therefore contain missing data.',
    'Las áreas ilegibles se rellenan con ceros y se registran; la imagen puede contener datos faltantes.',
    '无法读取的区域会填零并记录；因此镜像可能缺失数据。',
    'Нечитаемые участки заменяются нулями и отмечаются; образ может содержать пропуски данных.',
    '読み取れない領域はゼロで埋めて記録します。そのためイメージに欠落部分が残る可能性があります。')
add('Achtung: Schon das Lesen kann eine physisch defekte Festplatte zusätzlich belasten. Für beschädigte Hardware zuerst ein sektorweises Abbild erstellen.',
    'Caution: Even read-only access can further stress a physically failing drive. Image it first.',
    'Atención: incluso leer puede afectar a un disco dañado. Cree primero una imagen.',
    '注意：即使只读访问也可能加重故障硬盘负担。请先制作镜像。',
    'Внимание: даже чтение может ухудшить состояние неисправного диска. Сначала создайте образ.',
    '注意：読み取りだけでも故障ドライブに負担がかかる場合があります。先にイメージを作成してください。')
add('Achtung: Schon das Lesen kann eine physisch defekte Festplatte zusätzlich belasten. Weitere Zugriffe möglichst vermeiden und zuerst ein schonendes Image mit geeigneten Werkzeugen erstellen.',
    'Caution: Even reading can further damage a failing drive. Minimize access; first create an image using suitable low-impact tools.',
    'Atención: incluso leer puede empeorar un disco defectuoso. Reduzca accesos y cree una imagen con herramientas adecuadas.',
    '注意：读取也可能加重故障磁盘损坏。尽量减少访问，先使用合适工具进行低负载镜像。',
    'Внимание: даже чтение может ухудшить состояние диска. Ограничьте доступ и сначала создайте образ щадящими средствами.',
    '注意：読み取りだけでも故障ドライブの状態が悪化する場合があります。アクセスを最小限にし、適切なツールで低負荷のイメージを先に作成してください。')


# Display-only file metadata and export queue states. These never replace the
# canonical state used by recovery decisions or the resume manifest.
add('Datei', 'File', 'Archivo', '文件', 'Файл', 'ファイル')
add('Ordner', 'Folder', 'Carpeta', '文件夹', 'Папка', 'フォルダー')
add('Vorhanden', 'Existing', 'Existente', '现有', 'Существует', '存在')
add('Gelöscht', 'Deleted', 'Eliminado', '已删除', 'Удалено', '削除済み')
add('Ordner eingeschränkt', 'Folder (limited)', 'Carpeta (limitada)', '文件夹（受限）', 'Папка (ограничено)', 'フォルダー (制限あり)')
add('Nur Namenshinweis', 'Name hint only', 'Solo pista del nombre', '仅名称线索', 'Только имя', '名前の手掛かりのみ')
add('Gelöscht · unsicher', 'Deleted · uncertain', 'Eliminado · incierto', '已删除 · 不确定', 'Удалено · ненадёжно', '削除済み · 不確実')
add('Export möglich · ungeprüft', 'Export possible · unchecked', 'Exportable · sin verificar', '可导出 · 未验证', 'Экспорт возможен · не проверено', 'エクスポート可能 · 未検証')
add('Wartend', 'Waiting', 'En espera', '等待中', 'Ожидание', '待機中')
add('Läuft', 'Running', 'En curso', '进行中', 'Выполняется', '実行中')
add('Erfolgreich', 'Successful', 'Correcto', '成功', 'Успешно', '成功')
add('Übersprungen', 'Skipped', 'Omitido', '已跳过', 'Пропущено', 'スキップ')
add('Abgebrochen', 'Cancelled', 'Cancelado', '已取消', 'Отменено', 'キャンセル')
add('Beendet', 'Finished', 'Finalizado', '已完成', 'Завершено', '完了')
add('Verifiziert', 'Verified', 'Verificado', '已验证', 'Проверено', '検証済み')
add('Keine Dateidaten', 'No file data', 'Sin datos de archivo', '无文件数据', 'Нет данных файла', 'ファイルデータなし')


def display_kind_text(kind: str, language: str) -> str:
    """Translate file kind labels while leaving filename extensions intact."""
    if kind.endswith('-Datei'):
        suffix = {'de':'-Datei', 'en':' file', 'es':' archivo', 'zh':' 文件',
                  'ru':' файл', 'ja':' ファイル'}[language]
        return kind[:-len('-Datei')] + suffix
    return translate(kind, language)

# Frequent modal notifications and preview field names.
add('Bitte zuerst ein Datenträgerabbild auswählen.',
    'Select a disk image first.', 'Seleccione primero una imagen de disco.',
    '请先选择磁盘镜像。', 'Сначала выберите образ диска.', '先にディスクイメージを選択してください。')
add('Bitte eine geprüfte Partition auswählen.',
    'Select an inspected partition.', 'Seleccione una partición examinada.',
    '请选择已检查的分区。', 'Выберите проверенный раздел.', '検査済みのパーティションを選択してください。')
add('Bitte zuerst ein Dateisystem einlesen.',
    'Read a file system first.', 'Lea primero un sistema de archivos.',
    '请先读取文件系统。', 'Сначала прочитайте файловую систему.', '先にファイルシステムを読み込んでください。')
add('Bitte einen Zielpfad auswählen.',
    'Select a destination path.', 'Seleccione una ruta de destino.',
    '请选择目标路径。', 'Выберите путь назначения.', '保存先パスを選択してください。')
add('Noch kein vollständiger Exportbericht vorhanden.',
    'No complete export report available yet.', 'Aún no hay un informe completo de exportación.',
    '尚无完整的导出报告。', 'Полный отчёт об экспорте пока недоступен.', '完全なエクスポートレポートはまだありません。')
add('Ein Export läuft bereits.',
    'An export is already running.', 'Ya hay una exportación en curso.',
    '导出已在进行中。', 'Экспорт уже выполняется.', 'エクスポートはすでに実行中です。')
add('Rechts Dateien/Ordner auswählen (Strg/Umschalt für mehrere).',
    'Select files or folders on the right (Ctrl/Shift for multiple selections).',
    'Seleccione archivos o carpetas a la derecha (Ctrl/Mayús para varios).',
    '请在右侧选择文件或文件夹（Ctrl/Shift 可多选）。',
    'Выберите справа файлы или папки (Ctrl/Shift для нескольких).',
    '右側でファイルまたはフォルダーを選択してください (Ctrl/Shiftで複数選択)。')
add('Keine verwendbaren Windows-Laufwerke gefunden.',
    'No usable Windows volumes found.', 'No se encontraron unidades Windows utilizables.',
    '未找到可用的 Windows 卷。', 'Не найдены доступные тома Windows.', '利用できるWindowsドライブが見つかりません。')
add('Keine Wiederherstellung auf die Quelle speichern.',
    'Never save recovered data to the source.', 'Nunca guarde los datos recuperados en el origen.',
    '不要将恢复的数据保存到源磁盘。', 'Не сохраняйте данные на исходный диск.', '復旧データを元のディスクへ保存しないでください。')
for row in [
    ('Name:', 'Name:', 'Nombre:', '名称：', 'Имя:', '名前:'),
    ('Status:', 'Status:', 'Estado:', '状态：', 'Статус:', '状態:'),
    ('Rettbarkeit:', 'Recoverability:', 'Recuperabilidad:', '可恢复性：', 'Возможность восстановления:', '復旧可能性:'),
    ('Vorschau:', 'Preview:', 'Vista previa:', '预览：', 'Предпросмотр:', 'プレビュー:'),
    ('Dateisystem:', 'File system:', 'Sistema de archivos:', '文件系统：', 'Файловая система:', 'ファイルシステム:'),
    ('Info:', 'Info:', 'Información:', '信息：', 'Сведения:', '情報:'),
]: add(*row)
add('Nur Metadaten geprüft; Dateiinhalte ungeprüft.',
    'Metadata checked only; file contents unverified.',
    'Solo se comprobaron los metadatos; contenido sin verificar.',
    '仅检查了元数据；文件内容未经验证。',
    'Проверены только метаданные; содержимое файлов не проверено.',
    'メタデータのみ確認済み。ファイル内容は未検証です。')
add('Dateigröße vollständig gelesen; SHA-256 nur berechnet, nicht mit einem Original verglichen.',
    'Full declared file size read; SHA-256 calculated only, not compared with an original.',
    'Se leyó todo el tamaño declarado; SHA-256 calculado, sin comparar con un original.',
    '已读取完整声明长度；仅计算 SHA-256，未与原始文件比较。',
    'Прочитан весь заявленный размер; SHA-256 вычислена, но с оригиналом не сравнивалась.',
    '申告サイズをすべて読み取り済み。SHA-256は計算のみで、原本との比較は行っていません。')
add('Neue Exporte: Zieldatei gelesen und SHA-256 gespeichert. Kein erneuter Vergleich mit der Quelle.',
    'New exports: destination file read and SHA-256 saved. No separate comparison with the source.',
    'Nuevas exportaciones: destino leído y SHA-256 guardado. Sin comparación adicional con el origen.',
    '新导出：已读取目标文件并保存 SHA-256。未另行与源文件比较。',
    'Новый экспорт: файл назначения прочитан, SHA-256 сохранена. Отдельного сравнения с источником нет.',
    '新規出力：出力ファイルを読み取り、SHA-256を保存。元データとの再比較は行っていません。')
add('Fortsetzen: Größe und SHA-256 mit dem gespeicherten Export verglichen. Kein erneuter Vergleich mit der Quelle.',
    'Resume: size and SHA-256 compared with the saved export record. No new source comparison.',
    'Reanudación: tamaño y SHA-256 comparados con el registro guardado. Sin nueva comparación con el origen.',
    '继续导出：已将大小和 SHA-256 与保存的导出记录比较。未重新与源文件比较。',
    'Продолжение: размер и SHA-256 сверены с сохранённой записью экспорта. Источник повторно не сравнивался.',
    '再開：サイズとSHA-256を保存済み出力記録と比較。元データとの再比較は行っていません。')
add('Exportiert – Originalinhalt ungeprüft', 'Exported – original contents unverified',
    'Exportado: original sin verificar', '已导出－原始内容未经验证',
    'Экспортировано — оригинал не проверен', '出力済み－原本内容は未検証')
add('Export-Prüfsumme bestätigt', 'Export checksum confirmed', 'Suma de exportación confirmada',
    '导出校验和已确认', 'Контрольная сумма экспорта подтверждена', '出力チェックサムを確認済み')
add('Metadaten plausibel', 'Metadata plausible', 'Metadatos plausibles',
    '元数据合理', 'Метаданные правдоподобны', 'メタデータに整合性あり')
add('Linux-Datenträger: Leseberechtigung fehlt.',
    'Linux drive: read permission is missing.', 'Unidad Linux: falta permiso de lectura.',
    'Linux 磁盘：缺少读取权限。', 'Диск Linux: нет разрешения на чтение.',
    'Linuxドライブ：読み取り権限がありません。')
add('Geräteberechtigungen durch die Systemverwaltung gezielt für dieses Gerät prüfen lassen; nur Lesezugriff wird benötigt.',
    'Ask your system administrator to check permissions for this specific device; only read access is needed.',
    'Pida al administrador que revise los permisos de este dispositivo; solo se necesita acceso de lectura.',
    '请系统管理员检查此设备的权限；只需要读取权限。',
    'Попросите администратора проверить права именно на это устройство; нужен только доступ на чтение.',
    '管理者にこのデバイスの権限確認を依頼してください。必要なのは読み取り権限のみです。')
add('Alternativ ein vorhandenes Image öffnen. Danach die Quelle erneut auswählen. Tenshi ohne sudo starten.',
    'Alternatively, open an existing image. Select the source again after permissions are resolved. Run Tenshi without sudo.',
    'También puede abrir una imagen existente. Tras resolver los permisos, seleccione de nuevo el origen. Inicie Tenshi sin sudo.',
    '也可打开现有镜像。权限问题解决后重新选择来源。请勿使用 sudo 启动 Tenshi。',
    'Можно открыть готовый образ. После исправления прав выберите источник заново. Запускайте Tenshi без sudo.',
    '既存のイメージも利用できます。権限の問題を解決したらソースを選び直してください。Tenshiはsudoなしで起動してください。')
add('Tenshi ändert keine Geräteberechtigungen.', 'Tenshi does not change device permissions.',
    'Tenshi no cambia los permisos de dispositivos.', 'Tenshi 不会更改设备权限。',
    'Tenshi не изменяет права на устройства.', 'Tenshiはデバイスの権限を変更しません。')
add('Gerät:', 'Device:', 'Dispositivo:', '设备：', 'Устройство:', 'デバイス:')
add('Gerätekennung (Major:Minor):', 'Device ID (major:minor):', 'ID del dispositivo (mayor:menor):',
    '设备标识（主设备号:次设备号）：', 'Идентификатор устройства (major:minor):', 'デバイスID（major:minor）:')
add('Modell:', 'Model:', 'Modelo:', '型号：', 'Модель:', 'モデル:')
add('Gerätegröße (Bytes):', 'Device size (bytes):', 'Tamaño del dispositivo (bytes):',
    '设备大小（字节）：', 'Размер устройства (байт):', 'デバイス容量（バイト）:')
# Keep partial substitutions conservative: only anchored field labels and
add('Tenshi beenden','Quit Tenshi','Salir de Tenshi','退出 Tenshi','Закрыть Tenshi','Tenshiを終了')
add('Beim Beenden wurden Fehler gemeldet. Bitte prüfe die folgenden Meldungen; betroffene Dateien oder Prüfpunkte sind möglicherweise nicht vollständig gespeichert.',
    'Errors were reported while quitting. Please review the following messages; affected files or checkpoints may not have been fully saved.',
    'Se notificaron errores al salir. Revise los siguientes mensajes; es posible que los archivos o puntos de control afectados no se hayan guardado por completo.',
    '退出时报告了错误。请检查以下消息；相关文件或检查点可能未完整保存。',
    'При завершении возникли ошибки. Проверьте следующие сообщения: затронутые файлы или контрольные точки могли сохраниться не полностью.',
    '終了中にエラーが報告されました。以下のメッセージを確認してください。該当するファイルやチェックポイントが完全に保存されていない可能性があります。')
add('Es laufen noch Export-, Image- oder Speichervorgänge. Beim Beenden werden Export und Imageerstellung kontrolliert unterbrochen. Tenshi wartet auf das Ende laufender Schreibvorgänge. Jetzt unterbrechen und Tenshi schließen?',
    'Export, imaging or save operations are still running. Quitting will request a controlled pause of export and imaging. Tenshi will wait for active writes to finish. Interrupt now and quit Tenshi?',
    'Todavía hay operaciones de exportación, imagen o guardado en curso. Al salir se solicitará una pausa controlada de la exportación y la creación de imágenes. Tenshi esperará a que terminen las escrituras activas. ¿Interrumpir ahora y salir de Tenshi?',
    '导出、镜像创建或保存操作仍在运行。退出时将请求有序中断导出和镜像创建。Tenshi 会等待正在进行的写入结束。现在中断并退出 Tenshi 吗？',
    'Ещё выполняются экспорт, создание образа или сохранение. При выходе будет запрошена контролируемая остановка экспорта и создания образа. Tenshi дождётся завершения текущих операций записи. Прервать и закрыть Tenshi?',
    'エクスポート、イメージ作成、または保存が実行中です。終了するとエクスポートとイメージ作成に中断を要求し、進行中の書き込みが終わるまで待ちます。中断してTenshiを終了しますか？')
add('Unterbrechung angefordert. Warte auf das Ende laufender Vorgänge …',
    'Interruption requested. Waiting for running operations to finish …',
    'Interrupción solicitada. Esperando a que terminen las operaciones en curso …',
    '已请求中断。正在等待运行中的操作结束…',
    'Запрошено прерывание. Ожидание завершения текущих операций …',
    '中断を要求しました。実行中の処理が終わるのを待っています…')
add('Lesbar gespeichert','Read and saved','Leído y guardado','已读取并保存','Прочитано и сохранено','読み取り・保存済み')
add('Lesefehler / Nullersatz','Read error / zero fill','Error de lectura / ceros','读取错误 / 填零','Ошибка чтения / заполнено нулями','読み取りエラー／ゼロ埋め')
add('Teilweise gespeichert','Partially saved','Guardado parcialmente','已部分保存','Частично сохранено','一部保存済み')
add('Fehlerzuordnung unvollständig','Incomplete error map','Mapa de errores incompleto','错误位置映射不完整','Неполная карта ошибок','エラーマップ未完成')
add('Einstellungen / fortsetzen','Settings / resume','Opciones / continuar','设置 / 继续','Настройки / продолжить','設定／再開')
add('100 Felder = 100 % der Quellbytes.','100 cells = 100% of source bytes.','100 celdas = 100 % de los bytes de origen.','100 格 = 来源字节总量的 100%。','100 ячеек = 100 % байтов источника.','100マス＝ソース全体の100%。')
add('Gespeichert: {percent:.1f} %','Saved: {percent:.1f}%','Guardado: {percent:.1f} %','已保存：{percent:.1f}%','Сохранено: {percent:.1f} %','保存済み：{percent:.1f}%')
add('Nullersatz: {size} · Fehlerbereiche: {count}','Zero-filled: {size} · Error ranges: {count}','Relleno con ceros: {size} · Rangos con errores: {count}','填零：{size} · 错误区域：{count}','Заполнено нулями: {size} · Диапазоны ошибок: {count}','ゼロ埋め：{size} · エラー範囲：{count}')
add('Quellbereiche, keine einzelnen Sektoren. Grün bedeutet lesbar gespeichert, keinen bestandenen Vollvergleich.',
    'Source ranges, not individual sectors. Green means read and saved, not a passed full comparison.',
    'Rangos del origen, no sectores individuales. Verde significa leído y guardado, no una comparación completa aprobada.',
    '显示来源区域，而非单个扇区。绿色表示已读取并保存，不表示已通过完整比较。',
    'Диапазоны источника, а не отдельные секторы. Зелёный означает чтение и сохранение, а не успешное полное сравнение.',
    '個々のセクターではなくソース範囲を表示します。緑は読み取り・保存済みを意味し、完全比較の合格を意味しません。')
add('Unterbrechung angefordert …','Pause requested …','Pausa solicitada …','已请求暂停…','Запрошена пауза …','中断を要求しました…')
add('Image-Erstellung fehlgeschlagen','Image creation failed','Error al crear la imagen','镜像创建失败','Создание образа не удалось','イメージ作成に失敗しました')
add('Image-Erstellung unterbrochen','Image creation paused','Creación de imagen pausada','镜像创建已暂停','Создание образа приостановлено','イメージ作成を中断しました')
add('Image-Erstellung beendet.','Image creation finished.','Creación de imagen finalizada.','镜像创建已完成。','Создание образа завершено.','イメージ作成が終了しました。')
add('Image wird erstellt …','Creating image …','Creando imagen …','正在创建镜像…','Создание образа …','イメージを作成中…')
add('Vollvergleich läuft …','Full comparison in progress …','Comparación completa en curso …','正在完整比较…','Выполняется полное сравнение …','完全比較中…')
add('NICHT bitgenau verifiziert','NOT verified bit-for-bit','NO verificado bit a bit','未通过逐位验证','НЕ проверено побитно','ビット単位の検証は未完了')
add('BITGENAU VERIFIZIERT: Vollvergleich mit Quelle bestanden.',
    'VERIFIED BIT-FOR-BIT: full comparison with source passed.',
    'VERIFICADO BIT A BIT: comparación completa con el origen aprobada.',
    '逐位验证成功：已通过与来源的完整比较。',
    'ПРОВЕРЕНО ПОБИТНО: полное сравнение с источником пройдено.',
    'ビット単位の検証済み：ソースとの完全比較に合格しました。')
add('Zugriff verweigert. Prüfe Leserechte für die Quelle und Schreibrechte für den Zielordner. Bei Flatpak muss der Zielordner auch für Tenshi freigegeben sein.',
    'Access denied. Check read access to the source and write access to the destination folder. In Flatpak, Tenshi must also have access to the destination folder.',
    'Acceso denegado. Compruebe los permisos de lectura del origen y de escritura de la carpeta de destino. En Flatpak, Tenshi también necesita acceso a esa carpeta.',
    '访问被拒绝。请检查来源的读取权限和目标文件夹的写入权限。使用 Flatpak 时，还必须允许 Tenshi 访问目标文件夹。',
    'Доступ запрещён. Проверьте права чтения источника и записи в папку назначения. В Flatpak также разрешите Tenshi доступ к этой папке.',
    'アクセスが拒否されました。ソースの読み取り権限と保存先の書き込み権限を確認してください。FlatpakではTenshiに保存先へのアクセスも許可する必要があります。')
add('Das Laufwerk ist schreibgeschützt eingebunden. Wähle einen beschreibbaren Zielordner oder prüfe die Einbindung und Freigabe.',
    'The drive is mounted read-only. Choose a writable destination folder or check the mount and sharing settings.',
    'La unidad está montada en modo de solo lectura. Elija una carpeta de destino con escritura o revise el montaje y los permisos compartidos.',
    '该驱动器以只读方式挂载。请选择可写入的目标文件夹，或检查挂载和共享设置。',
    'Диск подключён только для чтения. Выберите доступную для записи папку или проверьте параметры подключения и общего доступа.',
    'ドライブは読み取り専用でマウントされています。書き込み可能な保存先を選ぶか、マウントと共有設定を確認してください。')
add('Eine benötigte Dateioperation wird nicht unterstützt oder wurde als ungültig abgelehnt. Prüfe die Einbindung des Zielordners; gemeinsam genutzte VM-Ordner können eingeschränkt sein. Versuche einen lokalen Linux-Zielordner. Dies ist kein eindeutiger Nachweis fehlender Schreibrechte.',
    'A required file operation is unsupported or was rejected as invalid. Check the destination mount; shared VM folders may have limitations. Try a local Linux destination folder. This does not establish that write permission is missing.',
    'Una operación de archivo necesaria no está admitida o fue rechazada como no válida. Revise el montaje del destino; las carpetas compartidas de la VM pueden tener limitaciones. Pruebe una carpeta local de Linux. Esto no demuestra que falten permisos de escritura.',
    '所需的文件操作不受支持或被判定为无效。请检查目标的挂载设置；虚拟机共享文件夹可能存在限制。请尝试本地 Linux 目标文件夹。这并不能证明缺少写入权限。',
    'Нужная файловая операция не поддерживается или отклонена как недопустимая. Проверьте подключение папки назначения: общие папки ВМ могут иметь ограничения. Попробуйте локальную папку Linux. Это не доказывает отсутствие прав записи.',
    '必要なファイル操作が未対応、または無効として拒否されました。保存先のマウント設定を確認してください。仮想マシンの共有フォルダーには制限がある場合があります。Linuxのローカルフォルダーを試してください。書き込み権限の不足が確定したわけではありません。')
add('Auf dem Laufwerk ist kein Speicherplatz mehr verfügbar. Prüfe den freien Platz im Zielordner.',
    'The drive has no space left. Check free space at the destination folder.',
    'No queda espacio en la unidad. Compruebe el espacio libre en la carpeta de destino.',
    '驱动器空间不足。请检查目标文件夹所在驱动器的可用空间。',
    'На диске нет свободного места. Проверьте свободное место в папке назначения.',
    'ドライブの空き容量がありません。保存先の空き容量を確認してください。')
# fixed status fragments are eligible; do not translate a raw filename.
_PARTIAL = sorted(set(_PARTIAL + [s for s in TRANSLATIONS if s.endswith(':') and len(s)>=5]),
                  key=len, reverse=True)

# Destination assessment, before any export writes.
add('Exportauftrag öffnen','Open export job','Abrir trabajo de exportación','打开导出任务','Открыть задание экспорта','出力処理を開く')
add('Bisherigen Exportordner auswählen','Select previous export folder','Seleccionar carpeta de exportación anterior','选择原导出文件夹','Выбрать прежнюю папку экспорта','以前の出力フォルダーを選択')
add('Exportauftrag wird geprüft …','Checking export job …','Comprobando trabajo de exportación …','正在检查导出任务…','Проверка задания экспорта …','出力処理を確認中…')
add('Quelle und Auswahl werden nach Bestätigung erneut geprüft.','The source and selection are rechecked after confirmation.','La fuente y la selección se vuelven a comprobar tras confirmar.','确认后将重新检查来源和选择。','Источник и выбор повторно проверяются после подтверждения.','確認後にソースと選択を再検査します。')
add('Dateisystem für Wiederaufnahme: {done} / {total} Einträge geprüft …','Resume filesystem scan: {done} / {total} entries checked …','Análisis para reanudar: {done} / {total} entradas comprobadas …','继续任务的文件系统扫描：已检查 {done} / {total} 项…','Сканирование для продолжения: проверено {done} / {total} записей …','再開用の解析：{done} / {total} 件を確認…')
add('Gespeicherten Export fortsetzen?\n\nQuelle: {source}\nExportordner: {root}\nAusgewählte Einträge: {count}\n\nDie Quelle wird schreibgeschützt neu eingelesen und mit dem gespeicherten Auftrag verglichen. Fertige Dateien werden geprüft; unvollständige beginnen von vorn.',
    'Resume the saved export?\n\nSource: {source}\nExport folder: {root}\nSelected entries: {count}\n\nThe source is read again in read-only mode and compared with the saved job. Complete files are checked; incomplete files restart from the beginning.',
    '¿Reanudar la exportación guardada?\n\nFuente: {source}\nCarpeta de exportación: {root}\nEntradas seleccionadas: {count}\n\nLa fuente se vuelve a leer en modo de solo lectura y se compara con el trabajo guardado. Se comprueban los archivos completos; los incompletos empiezan de nuevo.',
    '继续已保存的导出任务？\n\n来源：{source}\n导出文件夹：{root}\n已选择项数：{count}\n\n将以只读方式重新读取来源，并与保存的任务比较。已完成的文件会重新检查；不完整的文件从头开始。',
    'Продолжить сохранённый экспорт?\n\nИсточник: {source}\nПапка экспорта: {root}\nВыбрано записей: {count}\n\nИсточник снова читается только для чтения и сравнивается с сохранённым заданием. Полные файлы проверяются; неполные копируются заново.',
    '保存済みの出力処理を再開しますか？\n\nソース：{source}\n出力フォルダー：{root}\n選択件数：{count}\n\nソースを読み取り専用で再解析し、保存済みの処理と比較します。完了済みファイルは検査し、不完全なファイルは最初から処理します。')
add('Ungültiger Exportauftrag.','Invalid export job.','Trabajo de exportación no válido.','导出任务无效。','Недопустимое задание экспорта.','出力処理が無効です。')
add('Ungültige gespeicherte Exportauswahl.','Invalid saved export selection.','Selección de exportación guardada no válida.','保存的导出选择无效。','Недопустимый сохранённый выбор экспорта.','保存された出力の選択が無効です。')
add('Im gewählten Ordner ist kein gespeicherter Exportauftrag vorhanden. Bitte den erzeugten Export-Unterordner wählen.',
    'The selected folder contains no saved export job. Please select the generated export subfolder.',
    'La carpeta seleccionada no contiene un trabajo guardado. Selecciona la subcarpeta de exportación generada.',
    '所选文件夹中没有保存的导出任务。请选择已生成的导出子文件夹。',
    'В выбранной папке нет сохранённого задания. Выберите созданную подпапку экспорта.',
    '選択したフォルダーに保存済みの処理がありません。生成された出力サブフォルダーを選んでください。')
add('Dieser Export enthält noch keine gespeicherte Auswahl. Bitte dieselbe Quelle, Auswahl und den ursprünglichen Zielordner manuell wählen.',
    'This export has no saved selection yet. Please manually select the same source, selection and original destination folder.',
    'Esta exportación aún no tiene una selección guardada. Selecciona manualmente la misma fuente, selección y carpeta de destino original.',
    '此导出尚未保存文件选择。请手动选择相同的来源、文件选择和原始目标文件夹。',
    'Этот экспорт ещё не содержит сохранённого выбора. Вручную выберите тот же источник, выбор и исходную папку назначения.',
    'この出力には選択情報がまだ保存されていません。同じソース、選択、元の保存先を手動で指定してください。')
add('Export-Statusdatei ist zu groß. Bitte den bisherigen manuellen Wiederaufnahmeweg verwenden.',
    'The export status file is too large. Please use the existing manual resume procedure.',
    'El archivo de estado es demasiado grande. Utiliza el procedimiento manual de reanudación.',
    '导出状态文件过大。请使用原有的手动继续方式。',
    'Файл состояния экспорта слишком велик. Используйте прежний ручной способ продолжения.',
    '出力状態ファイルが大きすぎます。従来の手動の再開手順を使用してください。')
add('Export-Statusdatei wurde während des Öffnens geändert.','The export status file changed while being opened.','El archivo de estado cambió durante su apertura.','导出状态文件在打开时发生变化。','Файл состояния изменился при открытии.','出力状態ファイルが開く途中で変更されました。')
add('Exportauftrag darf nicht über einen symbolischen Link geöffnet werden.','An export job cannot be opened through a symbolic link.','No se puede abrir un trabajo mediante un enlace simbólico.','不能通过符号链接打开导出任务。','Нельзя открывать задание через символическую ссылку.','シンボリックリンク経由では出力処理を開けません。')
add('Exportauftrag muss eine reguläre Statusdatei sein.','The export job must be a regular status file.','El trabajo debe ser un archivo de estado normal.','导出任务必须是常规状态文件。','Задание должно быть обычным файлом состояния.','出力処理は通常の状態ファイルである必要があります。')
add('Bitte recoverydesk_status.json aus dem bisherigen Exportordner auswählen.','Please select recoverydesk_status.json from the previous export folder.','Selecciona recoverydesk_status.json de la carpeta de exportación anterior.','请选择原导出文件夹中的 recoverydesk_status.json。','Выберите recoverydesk_status.json из прежней папки экспорта.','以前の出力フォルダーにある recoverydesk_status.json を選んでください。')
add('Die gespeicherte Quelle ist keine reguläre Image-Datei.','The saved source is not a regular image file.','La fuente guardada no es un archivo de imagen normal.','保存的来源不是常规镜像文件。','Сохранённый источник не является обычным файлом образа.','保存されたソースは通常のイメージファイルではありません。')
add('Die gespeicherte Quelle wurde geändert oder ausgetauscht. Bitte Quelle und Exportauftrag prüfen.',
    'The saved source was changed or replaced. Please check the source and export job.',
    'La fuente guardada se ha modificado o sustituido. Comprueba la fuente y el trabajo de exportación.',
    '保存的来源已被修改或替换。请检查来源和导出任务。',
    'Сохранённый источник изменён или заменён. Проверьте источник и задание экспорта.',
    '保存されたソースが変更または交換されています。ソースと出力処理を確認してください。')
add('Die gespeicherte Auswahl ist nicht mehr vollständig vorhanden. Der Export wurde nicht fortgesetzt.',
    'The saved selection is no longer fully available. The export was not resumed.',
    'La selección guardada ya no está completa. La exportación no se ha reanudado.',
    '保存的选择已不完整。未继续导出。',
    'Сохранённый выбор больше не доступен полностью. Экспорт не продолжен.',
    '保存された選択が一部見つかりません。出力は再開していません。')
add('Der gespeicherte Exportplan passt nicht mehr zur Quelle. Der Export wurde nicht fortgesetzt.',
    'The saved export plan no longer matches the source. The export was not resumed.',
    'El plan guardado ya no coincide con la fuente. La exportación no se ha reanudado.',
    '保存的导出计划已与来源不符。未继续导出。',
    'Сохранённый план больше не соответствует источнику. Экспорт не продолжен.',
    '保存された出力計画がソースと一致しません。出力は再開していません。')
add('Nach Neustart: „Exportauftrag öffnen“ → erzeugten Tenshi_Export_…-Unterordner wählen. Beim manuellen Fortsetzen über „Stapel-Export“: gleiche Quelle und Auswahl, ursprünglicher Zielordner.',
    'After restart: “Open export job” → choose the generated Tenshi_Export_… subfolder. For manual resume via “Batch export”: same source and selection, original destination folder.',
    'Tras reiniciar: «Abrir trabajo de exportación» → elegir la subcarpeta Tenshi_Export_… generada. Para reanudar manualmente mediante «Exportación por lotes»: misma fuente y selección, carpeta de destino original.',
    '重启后：“打开导出任务” → 选择生成的 Tenshi_Export_… 子文件夹。通过“批量导出”手动继续时：使用相同来源和文件选择，并选择原始目标文件夹。',
    'После перезапуска: «Открыть задание экспорта» → созданная подпапка Tenshi_Export_…. Для ручного продолжения через пакетный экспорт: прежний источник и выбор, исходная папка назначения.',
    '再起動後：「出力処理を開く」→ 生成された Tenshi_Export_… サブフォルダーを選択。一括エクスポートから手動で再開する場合は、同じソースと選択、および元の保存先フォルダーを指定します。')
add('Exportziel prüfen', 'Check export destination', 'Comprobar destino de exportación', '检查导出目标', 'Проверить папку экспорта', '出力先を確認')
add('Exportziel wird geprüft …', 'Checking export destination …', 'Comprobando destino de exportación …', '正在检查导出目标…', 'Проверка папки экспорта …', '出力先を確認中…')
add('Export nicht gestartet.', 'Export not started.', 'Exportación no iniciada.', '未开始导出。', 'Экспорт не запущен.', '出力を開始していません。')
add('Nicht ermittelbar', 'Unavailable', 'No disponible', '无法确定', 'Не определено', '取得できません')
add('Exportziel: {target}', 'Export destination: {target}', 'Destino de exportación: {target}', '导出目标：{target}', 'Папка экспорта: {target}', '出力先：{target}')
add('Dateisystem des Ziels: {filesystem}', 'Destination filesystem: {filesystem}', 'Sistema de archivos del destino: {filesystem}', '目标文件系统：{filesystem}', 'Файловая система назначения: {filesystem}', '保存先のファイルシステム：{filesystem}')
add('Geplante Dateiinhalte: {size}', 'Planned file contents: {size}', 'Contenido de archivos previsto: {size}', '计划文件内容大小：{size}', 'Планируемый объём файлов: {size}', '予定ファイル内容量：{size}')
add('Zusätzlich benötigte Dateibytes (Obergrenze): {size}', 'Additional file bytes needed (upper estimate): {size}', 'Bytes adicionales necesarios (estimación superior): {size}', '额外所需文件字节数（估算上限）：{size}', 'Дополнительный объём файлов (верхняя оценка): {size}', '追加で必要なファイル容量（上限見積もり）：{size}')
add('Vollständig vorhandene Dateien zur erneuten Prüfung: {count}', 'Complete existing files to recheck: {count}', 'Archivos completos existentes por comprobar: {count}', '待重新检查的已有完整文件：{count}', 'Имеющиеся полные файлы для повторной проверки: {count}', '再検査する既存の完全なファイル：{count}')
add('Aktuell verfügbar: {size}', 'Currently available: {size}', 'Disponible actualmente: {size}', '当前可用空间：{size}', 'Сейчас доступно: {size}', '現在の空き容量：{size}')
add('Der verfügbare Platz reicht voraussichtlich nicht aus. Wähle möglichst ein anderes Ziel oder gib dort Speicherplatz frei.',
    'The available space is likely insufficient. Choose another destination or free up space there if possible.',
    'El espacio disponible probablemente no sea suficiente. Elige otro destino o libera espacio si es posible.',
    '可用空间可能不足。请尽量选择其他目标或释放目标空间。',
    'Доступного места, вероятно, недостаточно. По возможности выберите другую папку назначения или освободите место.',
    '空き容量が不足する見込みです。可能であれば別の保存先を選ぶか、空き容量を増やしてください。')
add('{count} Dateien überschreiten die FAT/FAT32-Grenze von 4 GiB minus 1 Byte. Bitte ein anderes Exportziel wählen.',
    '{count} files exceed the FAT/FAT32 limit of 4 GiB minus 1 byte. Please choose another export destination.',
    '{count} archivos superan el límite FAT/FAT32 de 4 GiB menos 1 byte. Elige otro destino de exportación.',
    '{count} 个文件超过 FAT/FAT32 的 4 GiB 减 1 字节限制。请选择其他导出目标。',
    '{count} файлов превышают предел FAT/FAT32 в 4 ГиБ минус 1 байт. Выберите другую папку экспорта.',
    '{count} 個のファイルが FAT/FAT32 の上限（4 GiB − 1 バイト）を超えています。別の出力先を選んでください。')
add('Die Dateigrößengrenze des Ziels ist unbekannt, etwa bei manchen VM- oder Netzwerkfreigaben.',
    'The destination file size limit is unknown, as with some VM or network shares.',
    'Se desconoce el límite de tamaño de archivo del destino, como en algunas carpetas compartidas de máquinas virtuales o de red.',
    '目标文件大小限制未知，例如某些虚拟机或网络共享。',
    'Ограничение размера файла неизвестно, например для некоторых общих папок виртуальных машин или сети.',
    '一部の仮想マシンやネットワーク共有など、保存先のファイルサイズ上限は不明です。')
add('Schätzung anhand der Metadaten, ohne zusätzliche Lesezugriffe auf Dateiinhalte. Dateisystem-, Berichts- und Prüfsummendateien benötigen zusätzlichen Platz. Verfügbarer Speicher kann sich ändern.',
    'Estimate based on metadata, without additional reads of file contents. Filesystem metadata, reports and checksum files need additional space. Available space may change.',
    'Estimación basada en metadatos, sin lecturas adicionales del contenido. Los metadatos del sistema de archivos, informes y sumas requieren espacio adicional. El espacio disponible puede cambiar.',
    '估算基于元数据，不额外读取文件内容。文件系统元数据、报告和校验文件还需额外空间。可用空间可能变化。',
    'Оценка по метаданным без дополнительного чтения содержимого. Метаданные файловой системы, отчёты и контрольные суммы требуют дополнительного места. Свободное место может измениться.',
    'メタデータによる見積もりで、ファイル内容の追加読み取りは行いません。ファイルシステムのメタデータ、レポート、チェックサムには別途容量が必要です。空き容量は変動します。')
add('Export jetzt starten? Fertige Dateien werden geprüft; unvollständige beginnen von vorn. Fremde Dateien bleiben erhalten.',
    'Start export now? Finished files are checked; incomplete files restart from the beginning. Unknown files are preserved.',
    '¿Iniciar la exportación? Se comprueban los archivos terminados; los incompletos comienzan de nuevo. Se conservan los archivos ajenos.',
    '现在开始导出？已完成的文件将被检查；不完整的文件从头开始。其他文件会保留。',
    'Начать экспорт? Готовые файлы проверяются; неполные копируются заново. Посторонние файлы сохраняются.',
    '出力を開始しますか？完了済みファイルは検査し、不完全なファイルは最初から処理します。既存の無関係なファイルは保持します。')

# Extended content checks and isolated previews.
add('Bitte mindestens eine Datei auswählen.','Select at least one file.','Selecciona al menos un archivo.','请至少选择一个文件。','Выберите хотя бы один файл.','ファイルを1つ以上選択してください。')
add('Zurück','Previous','Anterior','上一个','Назад','前へ')
add('Weiter','Next','Siguiente','下一个','Далее','次へ')
add('Datei {current} von {total}','File {current} of {total}','Archivo {current} de {total}','文件 {current}／{total}','Файл {current} из {total}','ファイル {current}／{total}')
add('Exportierte Datei prüfen …','Check exported file …','Comprobar archivo exportado …','检查导出的文件…','Проверить экспортированный файл …','出力したファイルを検査…')
add('Bilder / PDF / Office','Images / PDF / Office','Imágenes / PDF / Office','图像／PDF／Office','Изображения / PDF / Office','画像／PDF／Office')
add('Bitte eine reguläre Datei ohne symbolische Verknüpfung wählen.',
    'Choose a regular file without a symbolic link.','Elige un archivo regular sin enlace simbólico.','请选择没有符号链接的常规文件。','Выберите обычный файл без символической ссылки.','シンボリックリンクではない通常ファイルを選択してください。')
add('Datei wurde während der Prüfung geändert.',
    'The file changed during the check.','El archivo cambió durante la comprobación.','文件在检查期间发生了变化。','Во время проверки файл изменился.','検査中にファイルが変更されました。')
add('Inhalt prüfen: Bilder, erste PDF-Seite und Office-Paketstruktur, höchstens 32 MiB.',
    'Check contents: images, the first PDF page and Office package structure, up to 32 MiB.',
    'Comprobar contenido: imágenes, primera página PDF y estructura del paquete Office, hasta 32 MiB.',
    '检查内容：图像、PDF 第一页及 Office 包结构，最多 32 MiB。',
    'Проверка содержимого: изображения, первая страница PDF и структура пакета Office, до 32 МиБ.',
    '内容検査：画像、PDF の最初のページ、Office パッケージ構造。32 MiB まで。')
add('OLE-/geschützter Office-Container. Alte Office-Formate und verschlüsselte Office-Dateien werden hier nicht geprüft.',
    'OLE/protected Office container. Legacy Office formats and encrypted Office files are not checked here.',
    'Contenedor Office OLE/protegido. Aquí no se comprueban formatos Office antiguos ni archivos cifrados.',
    'OLE／受保护的 Office 容器。此处不检查旧版 Office 格式及加密的 Office 文件。',
    'Контейнер Office OLE/защищённый. Старые форматы и зашифрованные файлы Office здесь не проверяются.',
    'OLE／保護された Office コンテナーです。旧形式や暗号化された Office ファイルはここでは検査しません。')
add('Struktur lesbar',
    'Readable structure',
    'Estructura legible',
    '结构可读',
    'Структура читается',
    '構造を読み取り可能')
add('Teilprüfung',
    'Partial check',
    'Comprobación parcial',
    '部分检查',
    'Частичная проверка',
    '部分検査')
add('Nicht als unterstütztes Format lesbar',
    'Unreadable as a supported format',
    'No se puede leer como formato compatible',
    '无法按支持的格式读取',
    'Не читается как поддерживаемый формат',
    '対応形式として読み取れません')
add('Prüfgrenze erreicht',
    'Check limit reached',
    'Límite de comprobación alcanzado',
    '已达到检查限制',
    'Достигнут предел проверки',
    '検査上限に達しました')
add('Nicht geprüft',
    'Not checked',
    'Sin comprobar',
    '未检查',
    'Не проверено',
    '未検査')
add('Verschlüsselt / geschützt',
    'Encrypted / protected',
    'Cifrado / protegido',
    '已加密／受保护',
    'Зашифровано / защищено',
    '暗号化／保護されています')
add('Bilddaten dekodiert: {width} × {height} Pixel.',
    'Image data decoded: {width} × {height} pixels.',
    'Imagen decodificada: {width} × {height} píxeles.',
    '图像数据已解码：{width} × {height} 像素。',
    'Изображение декодировано: {width} × {height} пикселей.',
    '画像データを復号：{width} × {height} ピクセル。')
add('Erstes Bild dekodiert: {width} × {height} Pixel. Weitere Animationsbilder sind nicht geprüft.',
    'First frame decoded: {width} × {height} pixels. Other animation frames are unchecked.',
    'Primer fotograma decodificado: {width} × {height} píxeles. Los demás no se han comprobado.',
    '首帧已解码：{width} × {height} 像素。其余动画帧未检查。',
    'Первый кадр декодирован: {width} × {height} пикселей. Остальные кадры не проверены.',
    '最初のフレームを復号：{width} × {height} ピクセル。他のアニメーションフレームは未検査です。')
add('PDF mit {pages} Seiten erkannt. Nur die erste Seite wurde gerendert; weitere Seiten, Anhänge und aktive Inhalte sind nicht geprüft.',
    'PDF with {pages} pages detected. Only page one was rendered; other pages, attachments and active content are unchecked.',
    'PDF de {pages} páginas detectado. Solo se ha representado la primera; las demás, los adjuntos y el contenido activo no están comprobados.',
    '检测到含 {pages} 页的 PDF。仅渲染了第一页；其他页面、附件和活动内容均未检查。',
    'Обнаружен PDF: {pages} стр. Отрисована только первая страница; остальные, вложения и активное содержимое не проверены.',
    '{pages} ページの PDF を検出。最初のページのみ描画し、他のページ、添付、アクティブコンテンツは未検査です。')
add('Office-Paket mit {members} Einträgen: ZIP-Prüfsummen und XML-Struktur lesbar. Darstellung, eingebettete Dateien und Makros sind nicht inhaltlich geprüft.',
    'Office package with {members} entries: ZIP checksums and XML structure are readable. Layout, embedded files and macros have not undergone content validation.',
    'Paquete Office de {members} entradas: sumas ZIP y estructura XML legibles. No se ha validado el contenido del diseño, archivos incrustados ni macros.',
    'Office 包含 {members} 个条目：ZIP 校验和及 XML 结构可读。未验证版式、嵌入文件或宏的内容。',
    'Пакет Office: {members} записей. Контрольные суммы ZIP и XML читаются. Содержимое макетов, вложенных файлов и макросов не проверено.',
    '{members} 項目の Office パッケージ：ZIP チェックサムと XML 構造を読み取り可能。レイアウト、埋め込みファイル、マクロの内容は未検査です。')
add('Das PDF benötigt ein Passwort oder erlaubt keine Vorschau. Es wurde nicht entschlüsselt.',
    'The PDF requires a password or disallows preview. It has not been decrypted.',
    'El PDF necesita contraseña o no permite la vista previa. No se ha descifrado.',
    '该 PDF 需要密码或不允许预览。尚未解密。',
    'PDF требует пароль или запрещает просмотр. Расшифровка не выполнялась.',
    'PDF にパスワードが必要か、プレビューが許可されていません。復号は行っていません。')
add('Das Office-Paket ist geschützt. Es wurde nicht entschlüsselt.',
    'The Office package is protected. It has not been decrypted.',
    'El paquete Office está protegido. No se ha descifrado.',
    'Office 包受保护，尚未解密。',
    'Пакет Office защищён. Расшифровка не выполнялась.',
    'Office パッケージは保護されています。復号は行っていません。')
add('Die Inhaltsprüfung und erweiterte Vorschau sind auf 32 MiB pro Datei begrenzt.',
    'Content checks and extended previews are limited to 32 MiB per file.',
    'La comprobación y vista previa ampliada están limitadas a 32 MiB por archivo.',
    '内容检查及扩展预览限制为每个文件 32 MiB。',
    'Проверка содержимого и расширенный просмотр ограничены 32 МиБ на файл.',
    '内容検査と拡張プレビューは1ファイル32 MiBまでです。')
add('Zeit-, Speicher- oder Formatgrenze erreicht. Daraus folgt keine Beschädigung der Datei.',
    'A time, memory or format limit was reached. This does not establish file damage.',
    'Se alcanzó un límite de tiempo, memoria o formato. Esto no demuestra que el archivo esté dañado.',
    '已达到时间、内存或格式限制。这并不表明文件已损坏。',
    'Достигнут предел времени, памяти или формата. Это не доказывает повреждение файла.',
    '時間、メモリ、形式の上限に達しました。ファイルの破損を示すものではありません。')
add('Die getrennte Verarbeitung wurde beendet. Eine Beurteilung des Dateiinhalts ist nicht möglich.',
    'The separate process stopped. File contents cannot be assessed.',
    'El proceso separado terminó. No se puede evaluar el contenido.',
    '独立处理已停止，无法评估文件内容。',
    'Отдельный процесс завершён. Оценить содержимое невозможно.',
    '別プロセスでの処理が終了しました。内容を評価できません。')
add('Die Daten lassen sich nicht als unterstütztes Format lesen. Eine Beschädigung oder ein abweichender Dateityp ist möglich.',
    'The data cannot be read as a supported format. It may be damaged or belong to another file type.',
    'Los datos no se leen como formato compatible. Pueden estar dañados o ser de otro tipo de archivo.',
    '数据无法按支持的格式读取，可能已损坏或属于其他文件类型。',
    'Данные не читаются как поддерживаемый формат. Возможно повреждение или другой тип файла.',
    '対応形式として読み取れません。破損または別のファイル形式の可能性があります。')
add('Eine benötigte Komponente für dieses Format fehlt.',
    'A required component for this format is missing.',
    'Falta un componente necesario para este formato.',
    '缺少此格式所需的组件。',
    'Отсутствует компонент для этого формата.',
    'この形式に必要なコンポーネントがありません。')
add('Für ZIP-Archive steht die ZIP-Prüfung im Exportbericht zur Verfügung.',
    'ZIP archives can be checked using the ZIP check in the export report.',
    'Los archivos ZIP se pueden comprobar desde el informe de exportación.',
    'ZIP 归档可通过导出报告中的 ZIP 检查进行检查。',
    'Для архивов ZIP доступна проверка в отчёте экспорта.',
    'ZIP アーカイブは出力レポートの ZIP 検査で確認できます。')
add('Für diesen Dateityp ist keine Inhaltsprüfung verfügbar.',
    'No content check is available for this file type.',
    'No hay comprobación de contenido para este tipo de archivo.',
    '此文件类型没有可用的内容检查。',
    'Для этого типа файла нет проверки содержимого.',
    'この種類のファイルには内容検査がありません。')
add('Die Prüfung bewertet lesbare Strukturen und Darstellbarkeit. Sie bestätigt weder vollständige Originalinhalte noch die Rettbarkeit gelöschter Daten. Links, Makros und Dokumentaktionen werden nicht ausgeführt.',
    'The check assesses readable structures and renderability. It does not confirm complete original contents or recoverability of deleted data. Links, macros and document actions are not executed.',
    'La comprobación evalúa estructuras legibles y representación. No confirma contenidos originales completos ni recuperación de datos borrados. No se ejecutan enlaces, macros ni acciones del documento.',
    '此检查评估结构是否可读及能否呈现，不确认原始内容完整，也不确认已删除数据可恢复。不会执行链接、宏或文档操作。',
    'Проверка оценивает читаемость структуры и отображение. Она не подтверждает полноту оригинала или восстановимость удалённых данных. Ссылки, макросы и действия не выполняются.',
    '読み取れる構造と描画可否を検査します。元の内容の完全性や削除データの復元を保証しません。リンク、マクロ、文書アクションは実行しません。')
add('Inhalt prüfen',
    'Check contents',
    'Comprobar contenido',
    '检查内容',
    'Проверить содержимое',
    '内容を検査')
add('Inhaltsprüfung läuft …',
    'Checking contents …',
    'Comprobando contenido …',
    '正在检查内容…',
    'Проверка содержимого …',
    '内容を検査中…')
add('Inhaltsprüfung abgeschlossen.',
    'Content check finished.',
    'Comprobación de contenido finalizada.',
    '内容检查已完成。',
    'Проверка содержимого завершена.',
    '内容検査が終了しました。')
add('Prüfung abgebrochen.',
    'Check cancelled.',
    'Comprobación cancelada.',
    '检查已取消。',
    'Проверка отменена.',
    '検査を中止しました。')
add('Keine Inhaltsbestätigung möglich.',
    'Contents cannot be confirmed.',
    'No se puede confirmar el contenido.',
    '无法确认内容。',
    'Содержимое подтвердить невозможно.',
    '内容を確認できません。')
add('Die Inhaltsprüfung liest die ausgewählte Datei erneut. Möglichst zuerst ein Image erstellen. Jetzt lesen?',
    'The content check reads the selected file again. Create an image first if possible. Read now?',
    'La comprobación vuelve a leer el archivo seleccionado. Crea una imagen primero si es posible. ¿Leer ahora?',
    '内容检查会再次读取选定文件。建议先制作镜像。现在读取吗？',
    'Проверка повторно читает выбранный файл. По возможности сначала создайте образ. Читать сейчас?',
    '選択ファイルを再度読み取ります。可能なら先にイメージを作成してください。今すぐ読み取りますか？')
add('Vorschau: bis 128 KiB Text oder 32 MiB Bild-/Dokumentdaten. Keine Bestätigung der Originalinhalte.',
    'Preview: up to 128 KiB of text or 32 MiB of image/document data. Original contents are not confirmed.',
    'Vista previa: hasta 128 KiB de texto o 32 MiB de imagen/documento. No confirma los contenidos originales.',
    '预览：最多 128 KiB 文本或 32 MiB 图像／文档数据。不确认原始内容。',
    'Просмотр: до 128 КиБ текста или 32 МиБ изображений/документов. Исходное содержимое не подтверждается.',
    'プレビュー：テキスト128 KiB、画像・文書32 MiBまで。元の内容の確認ではありません。')

# Image signature search.
add('Bildsignaturen suchen','Search image signatures','Buscar firmas de imágenes','搜索图像签名','Поиск сигнатур изображений','画像シグネチャを検索')
add('Signatursuche erfordert ein reguläres Image.','Signature search requires a regular image file.','La búsqueda de firmas requiere un archivo de imagen normal.','签名搜索需要普通磁盘映像文件。','Для поиска сигнатур требуется обычный файл образа.','シグネチャ検索には通常のイメージファイルが必要です。')
add('Signaturfunde: zusammenhängende JPEG/PNG-Strukturen, keine Originalnamen oder Ordner. Belegte und freie Bereiche werden durchsucht; ein Fund beweist weder Löschung noch unversehrte Originalinhalte. Fragmentierte Dateien werden nicht zusammengesetzt.','Signature candidates: contiguous JPEG/PNG structures, without original names or folders. Both allocated and free areas are searched; a match proves neither deletion nor intact original contents. Fragmented files are not reassembled.','Candidatos por firma: estructuras JPEG/PNG contiguas, sin nombres ni carpetas originales. Se buscan zonas ocupadas y libres; un hallazgo no demuestra eliminación ni contenido original intacto. No se reconstruyen archivos fragmentados.','签名候选项：连续的 JPEG/PNG 结构，不含原始名称或文件夹。搜索已分配和空闲区域；找到结构不能证明文件已删除或原始内容完整。不会重组碎片文件。','Кандидаты по сигнатурам: непрерывные структуры JPEG/PNG без исходных имён и папок. Проверяются занятые и свободные области; находка не доказывает удаление или целостность оригинала. Фрагментированные файлы не собираются.','シグネチャ候補は連続した JPEG/PNG 構造で、元の名前やフォルダーは不明です。使用中と空き領域の両方を検索します。検出は削除や元の内容の完全性を証明しません。断片化ファイルは再構成しません。')
add('JPEG/PNG bis 32 MiB pro Fund. Maximal 1000 Funde und 5000 Anfangssignaturen; Prüfgrenzen können die Suche vorzeitig beenden. Das gesamte Image wird gelesen. Suche jetzt starten?','JPEG/PNG up to 32 MiB per candidate. At most 1000 candidates and 5000 starting signatures; limits may stop the search early. The entire image is read. Start search now?','JPEG/PNG de hasta 32 MiB por candidato. Máximo de 1000 hallazgos y 5000 firmas iniciales; los límites pueden detener la búsqueda antes de tiempo. Se lee toda la imagen. ¿Iniciar ahora?','每个 JPEG/PNG 候选项最大 32 MiB。最多 1000 个结果和 5000 个起始签名；达到限制可能提前停止搜索。将读取整个映像。现在开始搜索？','JPEG/PNG до 32 МиБ на кандидата. Не более 1000 находок и 5000 начальных сигнатур; ограничения могут остановить поиск раньше. Читается весь образ. Начать поиск?','JPEG/PNG は候補ごとに最大32 MiB。最大1000件、開始シグネチャ5000件で、上限により検索が早期終了する場合があります。イメージ全体を読みます。検索を開始しますか？')
add('Bildsignaturen werden gesucht …','Searching image signatures …','Buscando firmas de imágenes…','正在搜索图像签名…','Поиск сигнатур изображений…','画像シグネチャを検索中…')
add('Signatursuche: {done} / {total} MiB gelesen …','Signature search: {done} / {total} MiB read …','Búsqueda de firmas: {done} / {total} MiB leídos…','签名搜索：已读取 {done} / {total} MiB…','Поиск сигнатур: прочитано {done} / {total} МиБ…','シグネチャ検索：{done} / {total} MiB 読み取り済み…')
add('Signatursuche beendet: {count} Bildstrukturen.','Signature search finished: {count} image structures.','Búsqueda de firmas finalizada: {count} estructuras de imagen.','签名搜索结束：{count} 个图像结构。','Поиск сигнатур завершён: структур изображений — {count}.','シグネチャ検索完了：画像構造 {count} 件。')
add('Prüfgrenze erreicht; Ergebnis unvollständig.','Limit reached; results are incomplete.','Límite alcanzado; resultados incompletos.','已达到检查限制；结果不完整。','Достигнут предел; результаты неполные.','検査上限に達したため、結果は不完全です。')
add('Signaturfund · ungeprüft','Signature candidate · unverified','Candidato por firma · sin verificar','签名候选项 · 未验证','Кандидат по сигнатуре · не проверен','シグネチャ候補 · 未検証')
add('Zusammenhängende Bildstruktur erkannt. Originalname, Ordner und Löschstatus sind unbekannt. Vorschau und Inhaltsprüfung bestätigen keine unversehrten Originalinhalte.','Contiguous image structure detected. Original name, folder and deletion status are unknown. Preview and content checks do not prove intact original contents.','Estructura de imagen contigua detectada. Nombre original, carpeta y estado de eliminación desconocidos. La vista previa y la comprobación del contenido no demuestran que el original esté intacto.','检测到连续图像结构。原始名称、文件夹和删除状态未知。预览和内容检查不能证明原始内容完整。','Обнаружена непрерывная структура изображения. Исходное имя, папка и факт удаления неизвестны. Предпросмотр и проверка содержимого не доказывают целостность оригинала.','連続した画像構造を検出しました。元の名前、フォルダー、削除状態は不明です。プレビューと内容検査は元の内容の完全性を証明しません。')
add('Signaturfunde werden nicht als Analysesitzung gespeichert. Das Image erneut durchsuchen oder einen gespeicherten Exportauftrag öffnen.','Signature candidates are not saved as an analysis session. Search the image again or open a saved export job.','Los candidatos por firma no se guardan como sesión de análisis. Vuelve a buscar en la imagen o abre un trabajo de exportación guardado.','签名候选项不保存为分析会话。请重新搜索映像或打开已保存的导出任务。','Кандидаты по сигнатурам не сохраняются в сеансе анализа. Повторите поиск в образе или откройте сохранённое задание экспорта.','シグネチャ候補は解析セッションに保存されません。イメージを再検索するか、保存済みの出力処理を開いてください。')
