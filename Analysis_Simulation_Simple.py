# -*- coding: utf-8 -*-
"""
Analysis Simulation Simple - Vereinfachte modulare Simulation
==============================================================
Ein einfaches Grid-basiertes Wachstumssimulationssystem mit:
- 50×50 Grid
- 3 Driver (Wachstumsförderer)
- 3 Stopper (Wachstumsbegrenzer)
- Interaktive Auswahl
- Rhino 3D Visualisierung
"""

import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import random
import math


# ============================================================================
# CONFIG - Zentrale Konfiguration
# ============================================================================

class Config:
    """Zentrale Konfiguration für die Simulation"""
    
    # Grid-Einstellungen
    GRID_SIZE = 50
    CELL_SIZE = 3.0
    START_X = 25
    START_Y = 25
    MAX_ITERATIONS = 80
    
    # Driver-Gewichte
    WEIGHT_LIGHT = 8.0
    WEIGHT_ATTRACTOR = 12.0
    WEIGHT_CONNECTED = 6.0
    
    # Stopper-Einstellungen
    BOUNDARY_SIZE = 18  # Halbe Breite/Höhe des Rechtecks (also 36x36 Rechteck)
    MIN_WIDTH = 2
    MAX_LIGHT_DISTANCE = 3
    
    # Growth Point
    ATTRACTOR_X = 40
    ATTRACTOR_Y = 40
    
    # Multi-Cell Growth Einstellungen
    CELLS_PER_ITERATION_MIN = 3    # Mindestens 3 neue Zellen pro Iteration
    CELLS_PER_ITERATION_MAX = 5    # Maximal 5 neue Zellen pro Iteration
    TOP_CANDIDATES_POOL = 10       # Pool der besten Kandidaten für Auswahl
    
    # Farben (RGB)
    COLOR_NORMAL = (0, 255, 0)      # Grün
    COLOR_START = (255, 215, 0)     # Gold
    COLOR_ATTRACTOR = (255, 0, 0)   # Rot
    COLOR_BOUNDARY = (0, 0, 255)    # Blau


# ============================================================================
# SIMPLEGRID - 50×50 Grid-Verwaltung
# ============================================================================

class SimpleGrid:
    """Verwaltet ein 50×50 Grid von Zellen"""
    
    def __init__(self, size):
        self.size = size
        self.cells = [[0] * size for _ in range(size)]
    
    def get(self, x, y):
        """Gibt Zellenwert zurück (0 = leer, 1 = belegt)"""
        if self.in_bounds(x, y):
            return self.cells[y][x]
        return 0
    
    def set(self, x, y, value):
        """Setzt Zellenwert"""
        if self.in_bounds(x, y):
            self.cells[y][x] = value
    
    def in_bounds(self, x, y):
        """Prüft ob Koordinaten im Grid liegen"""
        return 0 <= x < self.size and 0 <= y < self.size
    
    def is_empty(self, x, y):
        """Prüft ob Zelle leer ist"""
        return self.in_bounds(x, y) and self.cells[y][x] == 0
    
    def is_alive(self, x, y):
        """Prüft ob Zelle belegt ist"""
        return self.in_bounds(x, y) and self.cells[y][x] == 1
    
    def count_alive(self):
        """Zählt alle belegten Zellen"""
        return sum(sum(row) for row in self.cells)
    
    def get_neighbors_4(self, x, y):
        """Gibt 4-Nachbarn zurück (N, S, E, W)"""
        neighbors = []
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                neighbors.append((nx, ny))
        return neighbors
    
    def count_alive_neighbors(self, x, y):
        """Zählt lebende 4-Nachbarn"""
        count = 0
        for nx, ny in self.get_neighbors_4(x, y):
            if self.is_alive(nx, ny):
                count += 1
        return count
    
    def get_frontier_cells(self):
        """Findet alle leeren Zellen die an belegte Zellen angrenzen"""
        frontier = []
        for y in range(self.size):
            for x in range(self.size):
                if self.is_empty(x, y):
                    # Prüfe ob mindestens ein Nachbar belegt ist
                    if self.count_alive_neighbors(x, y) > 0:
                        frontier.append((x, y))
        return frontier


# ============================================================================
# DRIVERMANAGER - 3 Driver an/aus + Score-Berechnung
# ============================================================================

class DriverManager:
    """Verwaltet die 3 Driver und berechnet Scores"""
    
    def __init__(self, config):
        self.config = config
        self.drivers = {
            'light': False,
            'attractor': False,
            'connected': False
        }
    
    def set_active_drivers(self, active_list):
        """Setzt welche Driver aktiv sind
        
        Args:
            active_list: Liste mit Namen der aktiven Driver z.B. ['light', 'attractor']
        """
        # Alle deaktivieren
        for key in self.drivers:
            self.drivers[key] = False
        
        # Gewählte aktivieren
        for driver_name in active_list:
            if driver_name in self.drivers:
                self.drivers[driver_name] = True
    
    def calculate_score(self, grid, x, y):
        """Berechnet Gesamt-Score für eine Zelle basierend auf aktiven Drivern
        
        Args:
            grid: Das SimpleGrid
            x, y: Position der zu bewertenden Zelle
            
        Returns:
            float: Gesamt-Score (höher = besser)
        """
        score = 0.0
        
        # Driver 1: light - Licht-Score (Wachstum Richtung Süd-Ost)
        if self.drivers['light']:
            light_score = self._calculate_light_score(x, y)
            score += light_score * self.config.WEIGHT_LIGHT
        
        # Driver 2: attractor - Growth Point bei (40, 40)
        if self.drivers['attractor']:
            attractor_score = self._calculate_attractor_score(x, y)
            score += attractor_score * self.config.WEIGHT_ATTRACTOR
        
        # Driver 3: connected - Verbindungs-Bonus (kompakte Formen)
        if self.drivers['connected']:
            connected_score = self._calculate_connected_score(grid, x, y)
            score += connected_score * self.config.WEIGHT_CONNECTED
        
        return score
    
    def _calculate_light_score(self, x, y):
        """Berechnet Licht-Score (Wachstum Richtung Süd-Ost)
        
        Süd-Ost bedeutet: höherer x und höherer y ist besser
        """
        # Normalisierte Distanz zur Süd-Ost-Ecke
        dist_x = x / float(self.config.GRID_SIZE)
        dist_y = y / float(self.config.GRID_SIZE)
        
        # Je näher an Süd-Ost, desto höher der Score
        return (dist_x + dist_y) / 2.0
    
    def _calculate_attractor_score(self, x, y):
        """Berechnet Attractor-Score (Nähe zu Growth Point bei (40, 40))"""
        dx = x - self.config.ATTRACTOR_X
        dy = y - self.config.ATTRACTOR_Y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Je näher am Attractor, desto höher der Score
        # Maximum Score bei Distanz 0, fällt ab mit Distanz
        max_distance = math.sqrt(2 * self.config.GRID_SIZE * self.config.GRID_SIZE)
        if max_distance == 0:
            return 1.0
        
        return 1.0 - (distance / max_distance)
    
    def _calculate_connected_score(self, grid, x, y):
        """Berechnet Connected-Score (Bonus für viele Nachbarn)"""
        # Je mehr lebende Nachbarn, desto höher der Score
        alive_neighbors = grid.count_alive_neighbors(x, y)
        return alive_neighbors / 4.0  # Normalisiert auf 0-1


# ============================================================================
# STOPPERMANAGER - 3 Stopper an/aus + Erlaubt-Prüfung
# ============================================================================

class StopperManager:
    """Verwaltet die 3 Stopper und prüft ob Zellen erlaubt sind"""
    
    def __init__(self, config):
        self.config = config
        self.stoppers = {
            'boundary': False,
            'min_width': False,
            'light_distance': False
        }
    
    def set_active_stoppers(self, active_list):
        """Setzt welche Stopper aktiv sind
        
        Args:
            active_list: Liste mit Namen der aktiven Stopper z.B. ['boundary', 'min_width']
        """
        # Alle deaktivieren
        for key in self.stoppers:
            self.stoppers[key] = False
        
        # Gewählte aktivieren
        for stopper_name in active_list:
            if stopper_name in self.stoppers:
                self.stoppers[stopper_name] = True
    
    def is_allowed(self, grid, x, y, start_x, start_y):
        """Prüft ob eine Zelle platziert werden darf
        
        Args:
            grid: Das SimpleGrid
            x, y: Position der zu prüfenden Zelle
            start_x, start_y: Start-Position (Mitte)
            
        Returns:
            bool: True wenn erlaubt, False wenn blockiert
        """
        # Stopper 1: boundary - Grundstücksgrenze (Kreis mit Radius 6 um Mitte)
        if self.stoppers['boundary']:
            if not self._check_boundary(x, y, start_x, start_y):
                return False
        
        # Stopper 2: min_width - Mindestbreite (mind. 2 Zellen breit)
        if self.stoppers['min_width']:
            if not self._check_min_width(grid, x, y):
                return False
        
        # Stopper 3: light_distance - Licht-Abstand (max. 3 Zellen vom Rand)
        if self.stoppers['light_distance']:
            if not self._check_light_distance(grid, x, y):
                return False
        
        return True
    
    def _check_boundary(self, x, y, center_x, center_y):
        """Prüft ob Zelle innerhalb der Boundary ist (RECHTECK)"""
        dx = abs(x - center_x)
        dy = abs(y - center_y)
        
        # Rechteck-Prüfung: Innerhalb von BOUNDARY_SIZE in beide Richtungen
        return dx <= self.config.BOUNDARY_SIZE and dy <= self.config.BOUNDARY_SIZE
    
    def _check_min_width(self, grid, x, y):
        """
        Prüfung für Mindestbreite von 2 Zellen.
        
        BOOTSTRAP-PHASE: Bei weniger als 4 Zellen wird Wachstum erlaubt,
        um eine 2×2 Basis zu bilden. Danach greift die normale Prüfung.
        
        STRENGE Prüfung: Die neue Zelle muss zusammen mit einem Nachbarn
        eine Struktur bilden die mindestens 2 Zellen breit ist.
        
        Erlaubt (2 breit horizontal):     Erlaubt (2 breit vertikal):
        ■ ●                               ■
                                          ●
        
        NICHT erlaubt (nur 1 breit):
        ■
        ●
        ■
        (Hier ist ● nur 1 breit weil links/rechts nichts ist)
        """
        
        # Bootstrap-Phase: Erlaube Wachstum bis 4 Zellen existieren
        # Damit kann sich eine 2×2 Basis bilden
        alive_count = grid.count_alive()
        if alive_count < 4:
            return True  # Erlaube Wachstum während Bootstrap
        
        # Ab hier: Normale Mindestbreiten-Prüfung
        # Prüfe: Hat die Zelle einen Nachbarn UND hat dieser Nachbar 
        # oder die Zelle selbst einen parallelen Nachbarn?
        
        # Horizontale Nachbarn prüfen
        has_left = grid.is_alive(x - 1, y)
        has_right = grid.is_alive(x + 1, y)
        
        # Vertikale Nachbarn prüfen  
        has_up = grid.is_alive(x, y - 1)
        has_down = grid.is_alive(x, y + 1)
        
        # Fall 1: Horizontal 2 breit - links ODER rechts ist belegt
        if has_left or has_right:
            # Prüfe ob diese horizontale Verbindung "breit" ist
            # D.h. die Zelle oder der Nachbar hat noch einen parallelen Nachbarn
            
            if has_left:
                # Ist links-oben oder links-unten auch belegt? Oder oben/unten von mir?
                if grid.is_alive(x - 1, y - 1) or grid.is_alive(x - 1, y + 1):
                    return True
                if has_up or has_down:
                    return True
            
            if has_right:
                # Ist rechts-oben oder rechts-unten auch belegt? Oder oben/unten von mir?
                if grid.is_alive(x + 1, y - 1) or grid.is_alive(x + 1, y + 1):
                    return True
                if has_up or has_down:
                    return True
        
        # Fall 2: Vertikal 2 breit - oben ODER unten ist belegt
        if has_up or has_down:
            if has_up:
                # Ist oben-links oder oben-rechts auch belegt? Oder links/rechts von mir?
                if grid.is_alive(x - 1, y - 1) or grid.is_alive(x + 1, y - 1):
                    return True
                if has_left or has_right:
                    return True
            
            if has_down:
                # Ist unten-links oder unten-rechts auch belegt? Oder links/rechts von mir?
                if grid.is_alive(x - 1, y + 1) or grid.is_alive(x + 1, y + 1):
                    return True
                if has_left or has_right:
                    return True
        
        # Keine 2-breite Struktur möglich
        return False
    
    def _check_light_distance(self, grid, x, y):
        """
        Prüft ob in mindestens EINER der 4 Richtungen (N/S/E/W)
        nach max. X Zellen eine FREIE Zelle ist.
        
        Beispiel mit MAX_LIGHT_DISTANCE = 3:
        - Schau nach Norden: Ist nach 1, 2, oder 3 Zellen eine freie Zelle? 
        - Schau nach Süden: Ist nach 1, 2, oder 3 Zellen eine freie Zelle?
        - Schau nach Osten: ...
        - Schau nach Westen: ...
        
        Wenn MINDESTENS EINE Richtung innerhalb von 3 Zellen frei ist → erlaubt
        Wenn ALLE 4 Richtungen nach 3 Zellen immer noch blockiert sind → blockiert
        """
        max_dist = self.config.MAX_LIGHT_DISTANCE  # z.B. 3 oder 4
        
        # Temporär setzen um zu prüfen wie es aussehen würde
        grid.set(x, y, 1)
        
        # 4 Richtungen prüfen (von Neumann Nachbarschaft)
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        
        found_free = False
        
        for dx, dy in directions:
            # In diese Richtung schauen
            for dist in range(1, max_dist + 1):
                check_x = x + (dx * dist)
                check_y = y + (dy * dist)
                
                # Außerhalb Grid = frei (Licht kommt von außen rein)
                if not grid.in_bounds(check_x, check_y):
                    found_free = True
                    break
                
                # Leere Zelle gefunden = Licht kommt durch
                if grid.is_empty(check_x, check_y):
                    found_free = True
                    break
                
                # Belegte Zelle → weiter schauen in diese Richtung
            
            if found_free:
                break
        
        # Zurücksetzen
        grid.set(x, y, 0)
        
        return found_free


# ============================================================================
# VISUALIZER - Rhino 3D-Boxen
# ============================================================================

class Visualizer:
    """Erstellt 3D-Boxen in Rhino zur Visualisierung"""
    
    def __init__(self, config):
        self.config = config
        self.layer_name = "AnalysisSimulation"
        self.boxes = []
    
    def ensure_layer(self):
        """Erstellt Layer falls nicht vorhanden"""
        if not rs.IsLayer(self.layer_name):
            rs.AddLayer(self.layer_name)
        return self.layer_name
    
    def clear(self):
        """Löscht alle Boxen"""
        if self.boxes:
            rs.DeleteObjects(self.boxes)
        self.boxes = []
    
    def draw_grid(self, grid, start_x, start_y, show_attractor=False, show_boundary=False):
        """Zeichnet das Grid als 3D-Boxen
        
        Args:
            grid: Das SimpleGrid
            start_x, start_y: Start-Position (für Gold-Farbe)
            show_attractor: Zeige Attractor-Marker (rot)
            show_boundary: Zeige Boundary-Kreis (blau)
        """
        self.ensure_layer()
        rs.EnableRedraw(False)
        
        # Grid-Boxen zeichnen
        for y in range(grid.size):
            for x in range(grid.size):
                if grid.is_alive(x, y):
                    # Farbe bestimmen
                    if x == start_x and y == start_y:
                        color = self.config.COLOR_START  # Gold für Startzelle
                    else:
                        color = self.config.COLOR_NORMAL  # Grün für normale Zellen
                    
                    box = self._make_box(x, y, color)
                    if box:
                        self.boxes.append(box)
        
        # Attractor-Marker (wenn aktiv)
        if show_attractor:
            marker = self._make_marker(
                self.config.ATTRACTOR_X,
                self.config.ATTRACTOR_Y,
                self.config.COLOR_ATTRACTOR
            )
            if marker:
                self.boxes.append(marker)
        
        # Boundary-Rechteck (wenn aktiv)
        if show_boundary:
            rectangle = self._make_boundary_rectangle(start_x, start_y)
            if rectangle:
                self.boxes.append(rectangle)
        
        rs.EnableRedraw(True)
    
    def _make_box(self, x, y, color):
        """Erstellt eine Box für eine Zelle"""
        cell = self.config.CELL_SIZE
        
        x0 = x * cell
        y0 = y * cell
        z0 = 0
        z1 = cell
        
        corners = [
            (x0, y0, z0),
            (x0 + cell, y0, z0),
            (x0 + cell, y0 + cell, z0),
            (x0, y0 + cell, z0),
            (x0, y0, z1),
            (x0 + cell, y0, z1),
            (x0 + cell, y0 + cell, z1),
            (x0, y0 + cell, z1)
        ]
        
        try:
            box = rs.AddBox(corners)
            if box:
                rs.ObjectColor(box, color)
                rs.ObjectLayer(box, self.layer_name)
                return box
        except:
            pass
        
        return None
    
    def _make_marker(self, x, y, color):
        """Erstellt einen kleinen Marker (Kugel) für Attractor"""
        cell = self.config.CELL_SIZE
        center = (x * cell + cell / 2.0, y * cell + cell / 2.0, cell / 2.0)
        
        try:
            sphere = rs.AddSphere(center, cell / 3.0)
            if sphere:
                rs.ObjectColor(sphere, color)
                rs.ObjectLayer(sphere, self.layer_name)
                return sphere
        except:
            pass
        
        return None
    
    def _make_boundary_rectangle(self, center_x, center_y):
        """Erstellt ein Rechteck für die Boundary"""
        cell = self.config.CELL_SIZE
        size = self.config.BOUNDARY_SIZE
        
        # Ecken des Rechtecks berechnen
        x_min = (center_x - size) * cell
        x_max = (center_x + size + 1) * cell
        y_min = (center_y - size) * cell
        y_max = (center_y + size + 1) * cell
        
        # Rechteck als Polyline zeichnen
        points = [
            (x_min, y_min, 0),
            (x_max, y_min, 0),
            (x_max, y_max, 0),
            (x_min, y_max, 0),
            (x_min, y_min, 0)  # Schließen
        ]
        
        try:
            rect = rs.AddPolyline(points)
            if rect:
                rs.ObjectColor(rect, self.config.COLOR_BOUNDARY)
                rs.ObjectLayer(rect, self.layer_name)
                return rect
        except:
            pass
        
        return None


# ============================================================================
# ANALYSISSIMULATION - Hauptklasse mit run()
# ============================================================================

class AnalysisSimulation:
    """Hauptklasse für die Analyse-Simulation"""
    
    def __init__(self):
        self.config = Config()
        self.grid = None
        self.driver_manager = None
        self.stopper_manager = None
        self.visualizer = None
    
    def run(self):
        """Führt die Simulation aus mit interaktiver Auswahl"""
        
        while True:
            print("=" * 60)
            print("ANALYSIS SIMULATION - Vereinfachte Version")
            print("=" * 60)
            
            # Initialisierung
            self.grid = SimpleGrid(self.config.GRID_SIZE)
            self.driver_manager = DriverManager(self.config)
            self.stopper_manager = StopperManager(self.config)
            self.visualizer = Visualizer(self.config)
            
            # Startzelle setzen
            start_x = self.config.START_X
            start_y = self.config.START_Y
            self.grid.set(start_x, start_y, 1)
            
            # Driver auswählen
            active_drivers = self._select_drivers()
            self.driver_manager.set_active_drivers(active_drivers)
            print("Aktive Driver: {}".format(active_drivers))
            
            # Stopper auswählen
            active_stoppers = self._select_stoppers()
            self.stopper_manager.set_active_stoppers(active_stoppers)
            print("Aktive Stopper: {}".format(active_stoppers))
            
            # Simulation ausführen
            self._run_growth()
            
            # Visualisierung
            self.visualizer.clear()
            show_attractor = 'attractor' in active_drivers
            show_boundary = 'boundary' in active_stoppers
            self.visualizer.draw_grid(
                self.grid,
                start_x,
                start_y,
                show_attractor,
                show_boundary
            )
            
            # Ergebnis anzeigen
            final_count = self.grid.count_alive()
            print("Simulation fertig! Anzahl Zellen: {}".format(final_count))
            rs.MessageBox(
                "Simulation abgeschlossen!\nAnzahl Zellen: {}".format(final_count),
                0,
                "Fertig"
            )
            
            # Nochmal?
            result = rs.MessageBox(
                "Nochmal eine Simulation durchführen?",
                4 | 32,
                "Nochmal?"
            )
            
            if result != 6:  # 6 = Ja
                print("Simulation beendet.")
                break
            
            # Alte Visualisierung löschen für nächste Runde
            self.visualizer.clear()
    
    def _select_drivers(self):
        """Interaktive Auswahl der Driver"""
        print("\n=== DRIVER AUSWAHL ===")
        print("1 = light (Licht-Score: Wachstum Richtung Süd-Ost)")
        print("2 = attractor (Growth Point bei (40, 40): Wachstum zum Hotspot)")
        print("3 = connected (Verbindungs-Bonus: Kompakte, runde Formen)")
        print("Eingabe z.B. '1,2' für Driver 1 und 2, 'A' für alle, 'N' für keine")
        
        input_str = rs.GetString("Driver auswählen", "A")
        if not input_str:
            input_str = "A"
        
        return self._parse_selection(input_str, ['light', 'attractor', 'connected'])
    
    def _select_stoppers(self):
        """Interaktive Auswahl der Stopper"""
        print("\n=== STOPPER AUSWAHL ===")
        print("1 = boundary (Grundstücksgrenze: Rechteck 36x36 um Mitte)")
        print("2 = min_width (Mindestbreite: Mind. 2 Zellen breit)")
        print("3 = light_distance (Licht-Abstand: Max. 3 Zellen vom Rand)")
        print("Eingabe z.B. '1,3' für Stopper 1 und 3, 'A' für alle, 'N' für keine")
        
        input_str = rs.GetString("Stopper auswählen", "A")
        if not input_str:
            input_str = "A"
        
        return self._parse_selection(input_str, ['boundary', 'min_width', 'light_distance'])
    
    def _parse_selection(self, input_str, options):
        """Parst Benutzer-Eingabe zu Liste von aktiven Optionen
        
        Args:
            input_str: Eingabe wie "1,2" oder "A" oder "N"
            options: Liste der verfügbaren Optionen
            
        Returns:
            Liste der gewählten Optionen
        """
        input_str = input_str.strip().upper()
        
        # "A" = Alle
        if input_str == "A":
            return options
        
        # "N" = Keine
        if input_str == "N":
            return []
        
        # Zahlen parsen
        selected = []
        parts = input_str.split(',')
        for part in parts:
            part = part.strip()
            if part.isdigit():
                index = int(part) - 1  # 1-basiert zu 0-basiert
                if 0 <= index < len(options):
                    selected.append(options[index])
        
        return selected
    
    def _run_growth(self):
        """Führt das Wachstum aus bis MAX_ITERATIONS erreicht sind oder keine Kandidaten mehr vorhanden"""
        start_x = self.config.START_X
        start_y = self.config.START_Y
        
        iterations = 0
        
        while iterations < self.config.MAX_ITERATIONS:
            # Finde Frontier-Zellen (leere Zellen die an belegte angrenzen)
            frontier = self.grid.get_frontier_cells()
            
            if not frontier:
                print("Keine Frontier-Zellen mehr verfügbar")
                break
            
            # Score alle Kandidaten
            scored_candidates = []
            for (x, y) in frontier:
                # Prüfe ob erlaubt (Stopper)
                if not self.stopper_manager.is_allowed(self.grid, x, y, start_x, start_y):
                    continue
                
                # Berechne Score (Driver)
                score = self.driver_manager.calculate_score(self.grid, x, y)
                scored_candidates.append(((x, y), score))
            
            if not scored_candidates:
                print("Keine gültigen Kandidaten mehr (alle von Stoppern blockiert)")
                break
            
            # Sortiere nach Score (höchster zuerst)
            scored_candidates.sort(key=lambda item: item[1], reverse=True)
            
            # Top-10 Kandidaten für Auswahl
            top_count = min(self.config.TOP_CANDIDATES_POOL, len(scored_candidates))
            top_candidates = scored_candidates[:top_count]
            
            # Zufällige Anzahl: 3 bis 5 (oder weniger wenn nicht genug Kandidaten)
            max_cells = min(self.config.CELLS_PER_ITERATION_MAX, len(top_candidates))
            min_cells = min(self.config.CELLS_PER_ITERATION_MIN, max_cells)
            cells_to_grow = random.randint(min_cells, max_cells)
            
            # Gewichtete Auswahl OHNE Zurücklegen (keine Duplikate)
            available_candidates = list(top_candidates)  # Kopie für Entfernung
            
            for _ in range(cells_to_grow):
                if not available_candidates:
                    break
                
                # Gewichte berechnen
                weights = [math.exp(score) for (pos, score) in available_candidates]
                total_weight = sum(weights)
                
                if total_weight <= 0:
                    # Fallback: erste verfügbare Zelle
                    chosen_idx = 0
                else:
                    # Gewichtete Zufallsauswahl
                    r = random.random() * total_weight
                    cumulative = 0
                    chosen_idx = 0
                    for i, w in enumerate(weights):
                        cumulative += w
                        if r <= cumulative:
                            chosen_idx = i
                            break
                
                # Zelle setzen
                chosen_pos = available_candidates[chosen_idx][0]
                self.grid.set(chosen_pos[0], chosen_pos[1], 1)
                
                # Aus Pool entfernen (keine Duplikate)
                available_candidates.pop(chosen_idx)
            
            iterations += 1
        
        final_count = self.grid.count_alive()
        print("Wachstum beendet mit {} Zellen nach {} Iterationen".format(final_count, iterations))


# ============================================================================
# MAIN - Startpunkt
# ============================================================================

def main():
    """Startet die Analyse-Simulation"""
    try:
        sim = AnalysisSimulation()
        sim.run()
    except Exception as e:
        print("FEHLER: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        rs.MessageBox("Fehler: {}".format(str(e)), 0, "Fehler")


if __name__ == "__main__":
    main()
else:
    main()
