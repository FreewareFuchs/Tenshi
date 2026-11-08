# XFS: erweiterte Bereichszähler

Der Linux-Lauf nach PR #144 scheiterte auf dem neueren Ubuntu-Prüfrechner
beim Lesen einer mit `mkfs.xfs` erzeugten Datei. Anstelle des Inhalts kamen
Nullbytes zurück. Die bisherigen PR-Prüfungen waren erfolgreich gewesen.

Bei v3-Inodes mit `XFS_DIFLAG2_NREXT64` liegt die Zahl der Datenextents als
64-Bit-Wert an Offset 24. Das bisherige 32-Bit-Feld an Offset 76 bezeichnet
dann Attributextents. Eine dort gelesene Null ist kein Beleg für eine Sparse-Datei.
Tenshi verwendet nun das durch die Inode-Kennung festgelegte Feld und prüft
die passende Superblock-Kennung sowie das vorgeschriebene Null-Padding.

Die vorhandene Grenze der Inline-Extent-Liste gilt weiterhin. Große Zähler
veranlassen keine entsprechend großen Schleifen oder Speicheranforderungen;
abgeschnittene Listen werden abgelehnt. Btree-Dateidaten werden dadurch nicht
zusätzlich unterstützt. Alte Inodes ohne die Kennung verwenden unverändert
den bisherigen 32-Bit-Zähler. Die Quelle wird ausschließlich gelesen.

Regressionen prüfen tatsächliche Vorschau- und Exportinhalte, widersprüchliche
Kennungen und einen Zähler über 32 Bit. Linux prüft zusätzlich unabhängig
formatierte XFS-Images mit Standardformat, ausdrücklich eingeschaltetem und
ausgeschaltetem `nrext64` und vergleicht die Quelle vor und nach dem Export.

Formatgrundlage: [XFS-Dokumentation: On-disk Inode](https://kernel.googlesource.com/pub/scm/fs/xfs/xfs-documentation/+/f512c164a1d0e83a54eabf757be689c3f8bc54a7/design/XFS_Filesystem_Structure/ondisk_inode.asciidoc).
