# -*- coding: utf-8 -*-
"""
Analysis Simulation Simple - Vereinfachte modulare Simulation
==============================================================
Ein einfaches Grid-basiertes Wachstumssimulationssystem mit:
- 15×15 Grid
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
    GRID_SIZE = 15
    CELL_SIZE = 3.0
    START_X = 7
    START_Y = 7
    MAX_CELLS = 50
    
    # Driver-Gewichte
    WEIGHT_LIGHT = 1.0
    WEIGHT_ATTRACTOR = 2.0
    WEIGHT_CONNECTED = 1.5
    
    # Stopper-Einstellungen
    BOUNDARY_RADIUS = 6
    MIN_WIDTH = 2
    MAX_LIGHT_DISTANCE = 3
    
    # Growth Point
    ATTRACTOR_X = 12
    ATTRACTOR_Y = 12
    
    # Farben (RGB)
    COLOR_NORMAL = (0, 255, 0)      # Grün
    COLOR_START = (255, 215, 0)     # Gold
    COLOR_ATTRACTOR = (255, 0, 0)   # Rot
    COLOR_BOUNDARY = (0, 0, 255)    # Blau
    
    # Wachstum
    MAX_ATTEMPTS = 1000


# ============================================================================
# SIMPLEGRID - 15×15 Grid-Verwaltung
# ============================================================================

class SimpleGrid:
    """Verwaltet ein 15×15 Grid von Zellen"""
    
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
        
        # Driver 2: attractor - Growth Point bei (12, 12)
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
        """Berechnet Attractor-Score (Nähe zu Growth Point bei (12, 12))"""
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
        """Prüft ob Zelle innerhalb der Boundary ist (Kreis mit Radius 6)"""
        dx = x - center_x
        dy = y - center_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        return distance <= self.config.BOUNDARY_RADIUS
    
    def _check_min_width(self, grid, x, y):
        """Prüft Mindestbreite (mind. 2 Zellen breit)
        
        Zählt Breite in horizontaler und vertikaler Richtung.
        Mindestens eine Richtung muss >= MIN_WIDTH sein.
        """
        # Horizontal zählen (inkl. Kandidat)
        count_h = 1
        # Links
        cx = x - 1
        while cx >= 0 and grid.is_alive(cx, y):
            count_h += 1
            cx -= 1
        # Rechts
        cx = x + 1
        while cx < grid.size and grid.is_alive(cx, y):
            count_h += 1
            cx += 1
        
        # Vertikal zählen
        count_v = 1
        # Oben
        cy = y - 1
        while cy >= 0 and grid.is_alive(x, cy):
            count_v += 1
            cy -= 1
        # Unten
        cy = y + 1
        while cy < grid.size and grid.is_alive(x, cy):
            count_v += 1
            cy += 1
        
        # Mindestens eine Richtung muss >= MIN_WIDTH sein
        return count_h >= self.config.MIN_WIDTH or count_v >= self.config.MIN_WIDTH
    
    def _check_light_distance(self, grid, x, y):
        """Prüft Licht-Abstand (max. 3 Zellen vom Rand)
        
        Berechnet kürzeste Distanz zu einer leeren Zelle oder zum Grid-Rand.
        """
        # Temporär setzen für Distanz-Berechnung
        grid.set(x, y, 1)
        
        # BFS um Distanz zur nächsten leeren Zelle zu finden
        from collections import deque
        
        visited = set()
        queue = deque([(x, y, 0)])
        visited.add((x, y))
        min_distance = 999
        
        while queue:
            cx, cy, dist = queue.popleft()
            
            # Rand des Grids zählt als "außen"
            if cx == 0 or cx == grid.size - 1 or cy == 0 or cy == grid.size - 1:
                min_distance = min(min_distance, dist)
                break
            
            for nx, ny in grid.get_neighbors_4(cx, cy):
                if (nx, ny) in visited:
                    continue
                
                # Leere Zelle gefunden = Licht erreicht
                if grid.is_empty(nx, ny):
                    min_distance = dist + 1
                    queue.clear()
                    break
                
                visited.add((nx, ny))
                queue.append((nx, ny, dist + 1))
        
        # Zurücksetzen
        grid.set(x, y, 0)
        
        return min_distance <= self.config.MAX_LIGHT_DISTANCE


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
        
        # Boundary-Kreis (wenn aktiv)
        if show_boundary:
            circle = self._make_boundary_circle(start_x, start_y)
            if circle:
                self.boxes.append(circle)
        
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
    
    def _make_boundary_circle(self, center_x, center_y):
        """Erstellt einen Kreis für die Boundary"""
        cell = self.config.CELL_SIZE
        radius = self.config.BOUNDARY_RADIUS * cell
        center = (center_x * cell + cell / 2.0, center_y * cell + cell / 2.0, 0)
        
        try:
            circle = rs.AddCircle(center, radius)
            if circle:
                rs.ObjectColor(circle, self.config.COLOR_BOUNDARY)
                rs.ObjectLayer(circle, self.layer_name)
                return circle
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
        print("2 = attractor (Growth Point bei (12, 12): Wachstum zum Hotspot)")
        print("3 = connected (Verbindungs-Bonus: Kompakte, runde Formen)")
        print("Eingabe z.B. '1,2' für Driver 1 und 2, 'A' für alle, 'N' für keine")
        
        input_str = rs.GetString("Driver auswählen", "A")
        if not input_str:
            input_str = "A"
        
        return self._parse_selection(input_str, ['light', 'attractor', 'connected'])
    
    def _select_stoppers(self):
        """Interaktive Auswahl der Stopper"""
        print("\n=== STOPPER AUSWAHL ===")
        print("1 = boundary (Grundstücksgrenze: Kreis mit Radius 6 um Mitte)")
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
        """Führt das Wachstum aus bis max. 50 Zellen erreicht sind"""
        start_x = self.config.START_X
        start_y = self.config.START_Y
        
        attempts = 0
        
        while self.grid.count_alive() < self.config.MAX_CELLS and attempts < self.config.MAX_ATTEMPTS:
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
                attempts += 1
                continue
            
            # Sortiere nach Score (höchster zuerst)
            scored_candidates.sort(key=lambda item: item[1], reverse=True)
            
            # Gewichtete Zufallsauswahl aus Top-Kandidaten
            top_count = min(5, len(scored_candidates))
            top_candidates = scored_candidates[:top_count]
            
            # Gewichte für Zufallsauswahl
            weights = []
            for (pos, score) in top_candidates:
                # Exponentieller Bonus für höhere Scores
                weight = math.exp(score)
                weights.append(weight)
            
            # Gewichtete Auswahl
            total_weight = sum(weights)
            if total_weight <= 0:
                chosen = top_candidates[0][0]
            else:
                r = random.random() * total_weight
                cumulative = 0
                chosen = top_candidates[0][0]
                for i, w in enumerate(weights):
                    cumulative += w
                    if r <= cumulative:
                        chosen = top_candidates[i][0]
                        break
            
            # Zelle setzen
            self.grid.set(chosen[0], chosen[1], 1)
            attempts = 0  # Reset bei Erfolg
        
        final_count = self.grid.count_alive()
        print("Wachstum beendet mit {} Zellen".format(final_count))


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
