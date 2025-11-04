"""Web scraper for property listings."""
import json
import time
import hashlib
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropertyScraper:
    """Main scraper for property listings."""

    def __init__(self, config_path: str = 'config/sites_config.json'):
        """Initialize scraper with configuration."""
        # Get the project root directory
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        # Build absolute path to config
        if not os.path.isabs(config_path):
            config_path = os.path.join(project_root, config_path)

        self.config_path = config_path  # Store for later use

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.settings = self.config['scraping_settings']
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.settings['user_agent']
        })

    def _generate_id(self, url: str, title: str) -> str:
        """Generate unique ID for a property."""
        unique_string = f"{url}:{title}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text."""
        if not text:
            return ''
        return ' '.join(text.strip().split())

    def _extract_property_data(self, listing_element, site_config: dict) -> Optional[Dict]:
        """Extract property data from listing element."""
        try:
            selectors = site_config['selectors']

            # Extract title
            title_elem = listing_element.select_one(selectors['title'])
            title = self._clean_text(title_elem.text) if title_elem else None

            if not title:
                return None

            # Extract price
            price_elem = listing_element.select_one(selectors['price'])
            price = self._clean_text(price_elem.text) if price_elem else 'N/A'

            # Extract location
            location_elem = listing_element.select_one(selectors['location'])
            location = self._clean_text(location_elem.text) if location_elem else 'N/A'

            # Extract link
            link_elem = listing_element.select_one(selectors['link'])
            if link_elem:
                url = link_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = urljoin(site_config['base_url'], url)
            else:
                url = ''

            if not url:
                return None

            # Extract bedrooms
            bedrooms_elem = listing_element.select_one(selectors.get('bedrooms', ''))
            bedrooms = self._clean_text(bedrooms_elem.text) if bedrooms_elem else 'N/A'

            # Extract area
            area_elem = listing_element.select_one(selectors.get('area', ''))
            area = self._clean_text(area_elem.text) if area_elem else 'N/A'

            # Generate unique ID
            external_id = self._generate_id(url, title)

            return {
                'external_id': external_id,
                'source': site_config['name'],
                'title': title,
                'price': price,
                'location': location,
                'bedrooms': bedrooms,
                'area': area,
                'url': url,
                'description': ''
            }

        except Exception as e:
            logger.error(f"Error extracting property data: {e}")
            return None

    def scrape_site(self, site_config: dict) -> List[Dict]:
        """
        Scrape properties from a single site.

        Args:
            site_config: Site configuration dictionary

        Returns:
            List of property dictionaries
        """
        properties = []

        if not site_config.get('enabled', False):
            logger.info(f"Skipping disabled site: {site_config['name']}")
            return properties

        logger.info(f"Scraping {site_config['name']}...")

        try:
            # Add delay between requests
            time.sleep(self.settings['delay_between_requests'])

            response = self.session.get(site_config['search_url'], timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all listing containers
            listing_containers = soup.select(site_config['selectors']['listing_container'])

            logger.info(f"Found {len(listing_containers)} listings on {site_config['name']}")

            for listing in listing_containers:
                property_data = self._extract_property_data(listing, site_config)
                if property_data:
                    properties.append(property_data)

        except requests.RequestException as e:
            logger.error(f"Error scraping {site_config['name']}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {site_config['name']}: {e}")

        logger.info(f"Successfully scraped {len(properties)} properties from {site_config['name']}")
        return properties

    def scrape_all_sites(self) -> List[Dict]:
        """
        Scrape all enabled sites.

        Returns:
            List of all property dictionaries from all sites
        """
        all_properties = []

        for site_config in self.config['sites']:
            properties = self.scrape_site(site_config)
            all_properties.extend(properties)

        logger.info(f"Total properties scraped: {len(all_properties)}")
        return all_properties

    def add_custom_site(self, site_config: dict):
        """
        Add a custom site configuration.

        Args:
            site_config: Dictionary with site configuration
        """
        required_fields = ['name', 'base_url', 'search_url', 'selectors']

        for field in required_fields:
            if field not in site_config:
                raise ValueError(f"Missing required field: {field}")

        # Add default values
        if 'enabled' not in site_config:
            site_config['enabled'] = True

        if 'scraper_type' not in site_config:
            site_config['scraper_type'] = 'custom'

        self.config['sites'].append(site_config)

        # Save updated config
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

        logger.info(f"Added custom site: {site_config['name']}")

    def disable_site(self, site_name: str):
        """Disable a site by name."""
        for site in self.config['sites']:
            if site['name'] == site_name:
                site['enabled'] = False

                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)

                logger.info(f"Disabled site: {site_name}")
                return True

        logger.warning(f"Site not found: {site_name}")
        return False

    def enable_site(self, site_name: str):
        """Enable a site by name."""
        for site in self.config['sites']:
            if site['name'] == site_name:
                site['enabled'] = True

                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)

                logger.info(f"Enabled site: {site_name}")
                return True

        logger.warning(f"Site not found: {site_name}")
        return False

    def get_enabled_sites(self) -> List[str]:
        """Get list of enabled site names."""
        return [site['name'] for site in self.config['sites'] if site.get('enabled', False)]
