from typing import List, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass
class ExtractedItem:
    """Represents an extracted menu item."""
    name: str
    price: Optional[float]
    confidence: float
    raw_text: str


class MenuParser:
    """
    Parser for extracting dish names and prices from OCR text.
    Uses regex patterns to identify menu items.
    """
    
    # Common price patterns in Indian menus
    PRICE_PATTERNS = [
        r'(?:Rs\.?|₹|INR)\s*(\d+(?:\.\d{2})?)',  # Rs. 120, ₹120, INR 120
        r'(\d+(?:\.\d{2})?)\s*(?:Rs\.?|₹|INR)',  # 120 Rs, 120₹
        r'[-–—]\s*(\d+(?:\.\d{2})?)\s*$',         # - 120 at end
        r'(\d+(?:\.\d{2})?)\s*/-',                 # 120/-
        r'\.\s*(\d+(?:\.\d{2})?)\s*$',            # . 120 at end
    ]
    
    # Patterns to clean dish names
    NOISE_PATTERNS = [
        r'\d+(?:\.\d{2})?\s*$',      # Trailing numbers
        r'^[\s\-–—\.]+',              # Leading dashes/dots
        r'[\s\-–—\.]+$',              # Trailing dashes/dots
        r'\s{2,}',                    # Multiple spaces
    ]
    
    # Common menu section headers to skip
    SECTION_HEADERS = {
        'breakfast', 'lunch', 'dinner', 'snacks', 'beverages', 'drinks',
        'starters', 'main course', 'desserts', 'specials', 'today',
        'menu', 'price', 'item', 'rs', 'inr'
    }
    
    def __init__(self):
        self.price_regex = [re.compile(p, re.IGNORECASE) for p in self.PRICE_PATTERNS]
    
    def extract_price(self, text: str) -> Tuple[Optional[float], str]:
        """
        Extract price from text and return remaining text.
        
        Returns:
            Tuple of (price, text_without_price)
        """
        for pattern in self.price_regex:
            match = pattern.search(text)
            if match:
                try:
                    price = float(match.group(1))
                    # Remove price from text
                    clean_text = pattern.sub('', text).strip()
                    return price, clean_text
                except (ValueError, IndexError):
                    continue
        
        return None, text
    
    def clean_dish_name(self, name: str) -> str:
        """Clean and normalize dish name."""
        # Remove noise patterns
        cleaned = name
        for pattern in self.NOISE_PATTERNS:
            cleaned = re.sub(pattern, ' ', cleaned)
        
        # Remove special characters but keep parentheses for portions
        cleaned = re.sub(r'[^\w\s\(\)\-]', '', cleaned)
        
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Title case
        cleaned = cleaned.strip().title()
        
        return cleaned
    
    def is_valid_item(self, name: str, price: Optional[float]) -> bool:
        """Check if extracted item is likely a valid menu item."""
        if not name or len(name) < 2:
            return False
        
        # Skip section headers
        if name.lower() in self.SECTION_HEADERS:
            return False
        
        # Must have reasonable length
        if len(name) > 100:
            return False
        
        # Price should be reasonable for Indian canteen (₹5 to ₹500)
        if price is not None and (price < 5 or price > 500):
            return False
        
        return True
    
    def parse_line(self, line: str) -> Optional[ExtractedItem]:
        """Parse a single line of OCR text."""
        if not line or len(line.strip()) < 3:
            return None
        
        original_line = line.strip()
        
        # Extract price
        price, name_text = self.extract_price(original_line)
        
        # Clean dish name
        clean_name = self.clean_dish_name(name_text)
        
        if not self.is_valid_item(clean_name, price):
            return None
        
        # Calculate confidence based on extraction quality
        confidence = 0.5
        if price is not None:
            confidence += 0.3
        if len(clean_name) > 5:
            confidence += 0.1
        if re.match(r'^[A-Z]', clean_name):
            confidence += 0.1
        
        return ExtractedItem(
            name=clean_name,
            price=price,
            confidence=min(confidence, 1.0),
            raw_text=original_line
        )
    
    def parse_menu_text(self, ocr_text: str) -> List[ExtractedItem]:
        """
        Parse full OCR text and extract all menu items.
        
        Args:
            ocr_text: Raw text from OCR
            
        Returns:
            List of extracted menu items
        """
        items = []
        lines = ocr_text.split('\n')
        
        for line in lines:
            item = self.parse_line(line)
            if item:
                items.append(item)
        
        # Sort by confidence
        items.sort(key=lambda x: x.confidence, reverse=True)
        
        return items
    
    def parse_tabular_text(self, ocr_text: str) -> List[ExtractedItem]:
        """
        Parse menu text that might be in tabular format.
        Handles cases where items and prices are separated by tabs or multiple spaces.
        """
        items = []
        lines = ocr_text.split('\n')
        
        for line in lines:
            # Split by tabs or multiple spaces
            parts = re.split(r'\t+|\s{3,}', line.strip())
            
            if len(parts) >= 2:
                # Assume last part might be price
                potential_price = parts[-1]
                potential_name = ' '.join(parts[:-1])
                
                # Try to extract price from last part
                price_match = re.search(r'(\d+(?:\.\d{2})?)', potential_price)
                if price_match:
                    try:
                        price = float(price_match.group(1))
                        clean_name = self.clean_dish_name(potential_name)
                        
                        if self.is_valid_item(clean_name, price):
                            items.append(ExtractedItem(
                                name=clean_name,
                                price=price,
                                confidence=0.8,
                                raw_text=line.strip()
                            ))
                            continue
                    except ValueError:
                        pass
            
            # Fall back to regular parsing
            item = self.parse_line(line)
            if item:
                items.append(item)
        
        return items


# Singleton instance
menu_parser = MenuParser()
