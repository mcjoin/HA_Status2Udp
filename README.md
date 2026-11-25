# Status2UDP (Loxone)

Home-Assistant-Integration, die Zustandsänderungen ausgewählter Entitäten per **UDP an einen Loxone Miniserver** sendet – ohne eine einzige Automation. Dazu erzeugt sie eine **Importvorlage für Loxone Config** (virtueller UDP-Eingang mit allen Befehlen).

## Funktionen

- Einrichtung über die UI: 1. Entitäten auswählen, 2. Miniserver konfigurieren
- Entitäten und Miniserver-Einstellungen jederzeit über **Konfigurieren** änderbar
- Ein/Aus-Zustände → `1`/`0`, numerische Zustände → Zahl (Punkt als Dezimaltrennzeichen)
- `unavailable`/`unknown` und nicht-numerische Zustände werden nicht gesendet (Loxone behält den letzten Wert)
- Beim Start und optional zyklisch (z. B. alle 300 s) werden alle Werte erneut gesendet – damit sind die Werte nach einem Neustart des Miniservers sofort wieder da
- Download einer **VIU_*.xml** für *Virtueller UDP Eingang → Vorlage importieren* in Loxone Config
- Mehrere Miniserver = mehrere Einträge der Integration

## Installation (HACS)

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → URL dieses Repositories, Kategorie **Integration**
2. „Status2UDP (Loxone)“ installieren und Home Assistant neu starten
3. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Status2UDP (Loxone)“

Manuell: Ordner `custom_components/status2udp` nach `<config>/custom_components/` kopieren.

## Nachrichtenformat

Jede Änderung wird als eigenes UDP-Paket gesendet:

```
<Präfix><entity_id>=<Wert>
ha/sensor.wohnzimmer_temperatur=21.5
ha/binary_sensor.haustuer=1
```

Das Präfix (Standard `ha/`) verhindert, dass sich Befehlserkennungen überschneiden (z. B. `sensor.x` ist in `binary_sensor.x` enthalten).

| HA-Zustand | gesendet |
|---|---|
| `on`, `true`, `home`, `open`, `locked`, `detected`, `playing`, `active` | `1` |
| `off`, `false`, `not_home`, `closed`, `unlocked`, `clear`, `idle`, `paused`, `inactive` | `0` |
| Zahl, z. B. `21.50` | `21.5` |
| `unavailable`, `unknown`, sonstiger Text | – (nicht gesendet) |

## Loxone-Vorlage

Einstellungen → Geräte & Dienste → Status2UDP → **Konfigurieren** → **Loxone-Importvorlage herunterladen**.

Der Link ist 30 Minuten gültig. In Loxone Config: *Virtuelle Eingänge* markieren → *Virtueller UDP Eingang* → *Vorlage importieren* → Datei wählen. Die Vorlage enthält:

- UDP-Port wie in der Integration eingestellt
- pro Entität einen Befehl mit Befehlserkennung `ha/<entity_id>=\v`
- digital/analog anhand des aktuellen Zustands, Einheit aus `unit_of_measurement`
- Name der Entität als Bezeichnung, `entity_id` als Kommentar

Nach Änderungen an der Entitätsauswahl oder dem Präfix die Vorlage erneut herunterladen und importieren.

## Entwicklung

```
pip install -r requirements_test.txt
pytest
```

Die Tests mit Home Assistant laufen nur unter Linux/macOS (bzw. in Docker/WSL).
