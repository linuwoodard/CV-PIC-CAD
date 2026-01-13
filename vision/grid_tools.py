"""
Grid utilities for aligning detected shapes.
Includes GridMapper class for converting grid references to pixel coordinates.
"""


class GridMapper:
    """
    Maps grid references (e.g., 'A1', 'C5') to pixel coordinates.
    Uses the same margin calculations as overlay_grid.py for consistency.
    """
    
    def __init__(self, image_width: int, image_height: int, rows: int = 10, cols: int = 10):
        """
        Initialize the grid mapper.
        
        Args:
            image_width: Width of the image in pixels
            image_height: Height of the image in pixels
            rows: Number of grid rows (default: 10 for A-J)
            cols: Number of grid columns (default: 10 for 1-10)
        """
        self.image_width = image_width
        self.image_height = image_height
        self.rows = rows
        self.cols = cols
        
        # Use the same margins as overlay_grid.py
        self.margin_top = 60
        self.margin_bottom = 40
        self.margin_left = 60
        self.margin_right = 40
        
        # Calculate grid dimensions
        self.grid_width = image_width - self.margin_left - self.margin_right
        self.grid_height = image_height - self.margin_top - self.margin_bottom
        
        # Calculate cell spacing
        self.x_spacing = self.grid_width / cols
        self.y_spacing = self.grid_height / rows
        
        # Define valid row letters (A-J for 10 rows)
        self.row_letters = [chr(ord('A') + i) for i in range(rows)]
    
    def _parse_grid_ref(self, grid_ref: str) -> tuple[int, int]:
        """
        Parse a grid reference string (e.g., 'A1', 'C5') into row and column indices.
        
        Args:
            grid_ref: Grid reference string (e.g., 'A1', 'C5')
        
        Returns:
            Tuple of (row_index, col_index) where both are 0-based
        
        Raises:
            ValueError: If grid reference is invalid
        """
        grid_ref = grid_ref.strip().upper()
        
        if not grid_ref:
            raise ValueError(f"Empty grid reference")
        
        # Extract row letter (first character)
        row_letter = grid_ref[0]
        
        # Extract column number (remaining characters)
        try:
            col_num = int(grid_ref[1:])
        except (ValueError, IndexError):
            raise ValueError(f"Invalid grid reference format: '{grid_ref}'. Expected format like 'A1' or 'C5'")
        
        # Validate row letter
        if row_letter not in self.row_letters:
            raise ValueError(f"Row letter '{row_letter}' is out of range. Valid rows: {self.row_letters[0]}-{self.row_letters[-1]}")
        
        # Convert row letter to index (A=0, B=1, ..., J=9)
        row_index = ord(row_letter) - ord('A')
        
        # Validate column number (1-based to 0-based)
        if col_num < 1 or col_num > self.cols:
            raise ValueError(f"Column number {col_num} is out of range. Valid columns: 1-{self.cols}")
        
        col_index = col_num - 1  # Convert to 0-based
        
        return row_index, col_index
    
    def get_center_of_cell(self, grid_str):
        """
        Parses 'A1' or 'A1_NE' into (x, y) pixels.
        """
        # 1. Split base cell and suffix (e.g., "A1_NE" -> "A1", "NE")
        parts = grid_str.strip().split('_')
        base_cell = parts[0]
        suffix = parts[1] if len(parts) > 1 else "C" # Default to Center
        
        # 2. Get the base center of the cell (Your existing logic)
        # (Assuming you have logic that turns 'A'->row_index, '1'->col_index)
        row_idx = ord(base_cell[0].upper()) - ord('A')
        col_idx = int(base_cell[1:]) - 1
        
        cell_width = self.image_width / self.cols
        cell_height = self.image_height / self.rows
        
        center_x = (col_idx * cell_width) + (cell_width / 2)
        center_y = (row_idx * cell_height) + (cell_height / 2)
        
        # 3. Apply The Nudge (Sub-grid offset)
        # We move 25% of the cell size in the requested direction
        offset_x = cell_width * 0.25
        offset_y = cell_height * 0.25
        
        nudge_map = {
            'C':  (0, 0),
            'N':  (0, -offset_y), # Remember: Y is usually 0 at the top in images!
            'S':  (0, offset_y),
            'E':  (offset_x, 0),
            'W':  (-offset_x, 0),
            'NE': (offset_x, -offset_y),
            'NW': (-offset_x, -offset_y),
            'SE': (offset_x, offset_y),
            'SW': (-offset_x, offset_y)
        }
        
        dx, dy = nudge_map.get(suffix, (0,0))
        
        return (int(center_x + dx), int(center_y + dy))


if __name__ == "__main__":
    # Test case: 1000x1000 image
    mapper = GridMapper(image_width=1000, image_height=1000, rows=10, cols=10)
    
    # Test coordinates
    test_cells = ['A1', 'E5', 'J10']
    
    print("GridMapper Test (1000x1000 image, 10x10 grid):")
    print("-" * 50)
    for cell in test_cells:
        try:
            x, y = mapper.get_center_of_cell(cell)
            print(f"{cell}: ({x}, {y})")
        except ValueError as e:
            print(f"{cell}: ERROR - {e}")
    
    # Test error handling
    print("\nError Handling Tests:")
    print("-" * 50)
    invalid_refs = ['Z99', 'A0', 'K5', 'A11', 'invalid']
    for ref in invalid_refs:
        try:
            x, y = mapper.get_center_of_cell(ref)
            print(f"{ref}: ({x}, {y})")
        except ValueError as e:
            print(f"{ref}: {e}")
