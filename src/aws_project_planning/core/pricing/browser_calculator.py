"""Browser-based AWS Calculator interaction using pyppeteer."""

import asyncio
import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

import pyppeteer
from pyppeteer import launch
from pyppeteer.errors import TimeoutError

from .web_calculator import AWSWebCalculator
from .calculator import ResourceConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSBrowserCalculator:
    """
    Browser-based AWS Calculator interaction.
    
    This service uses pyppeteer (headless Chrome) to interact with the 
    AWS Pricing Calculator web interface for more accurate pricing.
    """
    
    # AWS Calculator URLs
    BASE_URL = "https://calculator.aws"
    CALCULATOR_URL = f"{BASE_URL}/#/estimate"
    
    # Key selectors for the AWS Calculator - these may need updating as AWS UI changes
    SELECTORS = {
        # Page structure
        'header': 'header.awsui-header, .calc-header, .awsui-app-layout__header',
        'loading_finished': '.calculator-grand-total, .awsui-cards-card, .calculator-price, .cost-display',
        
        # Service addition
        'add_service_button': '.estimator__add-service-button, button:has-text("Add service"), .awsui-button-variant-primary',
        'service_search': 'input[placeholder*="service"], .awsui-select-option-filter input, input[type="search"]',
        'service_results': '.awsui-select-option, .service-option, [data-testid="service-option"]',
        'service_config_done': '.service-add-button, .configured-service-save-button, button:has-text("Add to my estimate")',
        
        # Pricing elements
        'grand_total': '.calculator-grand-total, .calculator-price, .cost-display',
        'service_container': '.service-calculation-container, .service-row',
        'service_title': '.service-title, .service-name',
        'service_price': '.service-total-value, .service-price'
    }
    
    def __init__(self, headless: bool = True, timeout: int = 120000, debug: bool = False):
        """
        Initialize browser calculator.
        
        Args:
            headless: Whether to run browser in headless mode
            timeout: Default timeout in milliseconds for page operations
            debug: Enable extra debugging features
        """
        self.headless = headless
        self.timeout = timeout
        self.debug = debug
        self.web_calculator = AWSWebCalculator()
        
    async def _launch_browser(self):
        """
        Launch a browser instance with appropriate configurations.
        
        Returns:
            Browser instance
        """
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920,1080'
        ]
        
        # Add specific args for debugging if needed
        if self.debug and not self.headless:
            browser_args.extend([
                '--auto-open-devtools-for-tabs',
                '--disable-web-security'
            ])
        
        return await launch(
            headless=self.headless,
            args=browser_args,
            defaultViewport={'width': 1920, 'height': 1080}
        )
    
    async def _debug_page_structure(self, page, output_dir=None):
        """
        Debug helper: Extract and save page structure to help identify proper selectors.
        
        Args:
            page: Page object
            output_dir: Directory to save debug info
        """
        if not self.debug:
            return
            
        logger.info("Debugging page structure...")
        
        try:
            # Get all buttons on the page
            buttons = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('button')).map(btn => {
                    return {
                        text: btn.textContent.trim(),
                        classes: btn.className,
                        id: btn.id,
                        disabled: btn.disabled,
                        visible: btn.offsetParent !== null
                    };
                });
            }''')
            
            # Get key page elements
            elements = await page.evaluate('''() => {
                function getElementInfo(selector) {
                    const elements = Array.from(document.querySelectorAll(selector));
                    return elements.map(el => {
                        return {
                            tag: el.tagName,
                            classes: el.className,
                            id: el.id,
                            text: el.textContent.trim().substring(0, 50) + (el.textContent.trim().length > 50 ? '...' : ''),
                            visible: el.offsetParent !== null
                        };
                    });
                }
                
                return {
                    // Page sections
                    headers: getElementInfo('header, .header, .awsui-header'),
                    mainContent: getElementInfo('main, .main, .content'),
                    
                    // UI Elements
                    buttons: getElementInfo('button, .awsui-button, [role="button"]'),
                    inputs: getElementInfo('input, textarea, select'),
                    
                    // Service elements
                    services: getElementInfo('.service, .service-row, .aws-service'),
                    prices: getElementInfo('.price, .cost, .cost-display, [data-testid*="price"]')
                };
            }''')
            
            # Save the page HTML and structure if output_dir is provided
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
                # Save page HTML
                html_content = await page.content()
                html_path = os.path.join(output_dir, "page_html.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                # Save element structure
                structure_path = os.path.join(output_dir, "page_structure.json")
                with open(structure_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "buttons": buttons,
                        "elements": elements
                    }, f, indent=2)
                    
                # Take a screenshot
                screenshot_path = os.path.join(output_dir, "page_screenshot.png")
                await page.screenshot({'path': screenshot_path, 'fullPage': True})
                
                logger.info(f"Page structure saved to {structure_path}")
                logger.info(f"Page HTML saved to {html_path}")
                logger.info(f"Page screenshot saved to {screenshot_path}")
        
        except Exception as e:
            logger.error(f"Error debugging page structure: {str(e)}")
    
    async def _find_active_selector(self, page, selectors):
        """
        Find the first selector from a list that exists on the page.
        
        Args:
            page: Page object
            selectors: List of alternative selectors to try
            
        Returns:
            Found selector or None
        """
        if isinstance(selectors, str):
            selectors = selectors.split(', ')
            
        for selector in selectors:
            try:
                count = await page.evaluate(f'document.querySelectorAll("{selector}").length')
                if count > 0:
                    logger.info(f"Found active selector: {selector} ({count} elements)")
                    return selector
            except Exception:
                continue
                
        return None
    
    async def _wait_for_selector(self, page, selector, timeout=None, visible=True):
        """
        Wait for a selector with logging and extended timeout.
        
        Args:
            page: Page object
            selector: CSS selector to wait for
            timeout: Timeout in milliseconds
            visible: Whether element should be visible
            
        Returns:
            Element handle or None if timeout
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            logger.info(f"Waiting for selector: {selector}")
            
            # Try each comma-separated selector option
            if ', ' in selector:
                # Try each selector alternative
                active_selector = await self._find_active_selector(page, selector)
                if active_selector:
                    return await page.waitForSelector(active_selector, {'visible': visible, 'timeout': timeout})
                else:
                    logger.warning(f"No matching selector found among alternatives: {selector}")
                    return None
            else:
                # Regular single selector
                return await page.waitForSelector(selector, {'visible': visible, 'timeout': timeout})
                
        except TimeoutError as e:
            logger.error(f"Timeout waiting for selector: {selector}")
            return None
    
    async def _safe_click(self, page, selector, timeout=None):
        """
        Safely click an element with retry logic.
        
        Args:
            page: Page object
            selector: CSS selector to click
            timeout: Timeout in milliseconds
            
        Returns:
            True if click was successful, False otherwise
        """
        # First find the active selector if multiple options are provided
        if ', ' in selector:
            active_selector = await self._find_active_selector(page, selector)
            if active_selector:
                selector = active_selector
            else:
                logger.warning(f"No matching selector found for click: {selector}")
                return False
        
        element = await self._wait_for_selector(page, selector, timeout)
        if not element:
            return False
            
        try:
            # Try a normal click first
            await element.click()
            logger.info(f"Clicked on {selector}")
            return True
        except Exception as e:
            logger.warning(f"Normal click failed on {selector}, trying evaluate: {str(e)}")
            
            try:
                # Try JavaScript click as backup
                await page.evaluate(f'document.querySelector("{selector}").click()')
                logger.info(f"Clicked on {selector} using JavaScript")
                return True
            except Exception as e:
                logger.error(f"Failed to click {selector}: {str(e)}")
                
                # If debug is enabled, dump the page structure to help identify issues
                if self.debug:
                    await self._debug_page_structure(page)
                
                return False
    
    async def _add_service_manually(self, page, resource: ResourceConfig):
        """
        Add a service manually through the AWS Calculator UI.
        
        Args:
            page: Page object
            resource: Resource configuration
            
        Returns:
            True if successful, False otherwise
        """
        # Map our services to AWS service names in the UI
        service_name_map = {
            "ec2": "EC2",
            "rds": "RDS",
            "s3": "S3"
        }
        
        # Get AWS service name to search for
        aws_service_name = service_name_map.get(resource.service)
        if not aws_service_name:
            logger.warning(f"Unsupported service for manual addition: {resource.service}")
            return False
            
        try:
            # Click Add Service button
            logger.info(f"Adding service {aws_service_name} manually")
            if not await self._safe_click(page, self.SELECTORS['add_service_button']):
                logger.error("Couldn't click Add Service button")
                
                # Debugging: Try to find actual Add Service button for future reference
                if self.debug:
                    add_buttons = await page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('button')).filter(btn => 
                            btn.textContent.toLowerCase().includes('add') || 
                            btn.textContent.toLowerCase().includes('service')
                        ).map(btn => {
                            return {
                                text: btn.textContent.trim(),
                                classes: btn.className,
                                id: btn.id,
                                visible: btn.offsetParent !== null
                            };
                        });
                    }''')
                    logger.info(f"Potential add buttons found: {json.dumps(add_buttons, indent=2)}")
                
                return False
                
            # Wait for service search to appear and type service name
            search_input = await self._wait_for_selector(page, self.SELECTORS['service_search'])
            if not search_input:
                logger.error("Service search not found")
                return False
                
            await search_input.type(aws_service_name)
            await asyncio.sleep(1)  # Wait for search results
            
            # Find and click the service in results
            service_found = False
            
            # First try with the specific service name
            service_selector = f"{self.SELECTORS['service_results']}:has-text('{aws_service_name}')"
            service_found = await self._safe_click(page, service_selector)
            
            # If that fails, try a more generic approach
            if not service_found:
                # Try the first result
                service_found = await self._safe_click(page, self.SELECTORS['service_results'])
                
            if not service_found:
                logger.error(f"Could not find service {aws_service_name} in the results")
                return False
                
            # Wait for configuration page and fill in details
            # This is service-specific and would need different implementations per service
            await asyncio.sleep(2)  # Wait for config page to load
            
            # For now just click the "Configure" or "Add to my estimate" button to proceed
            config_done = await self._safe_click(page, self.SELECTORS['service_config_done'])
            if not config_done:
                logger.error("Couldn't complete service configuration")
                return False
                
            # Wait for service to be added to estimate
            added_service = await self._wait_for_selector(page, self.SELECTORS['service_container'])
            if not added_service:
                logger.warning("Could not confirm service was added to estimate")
                
            return True
            
        except Exception as e:
            logger.error(f"Error adding service manually: {str(e)}")
            return False
    
    async def get_price_estimate(self, 
                               resources: List[ResourceConfig], 
                               screenshot_path: Optional[str] = None,
                               debug_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed price estimate by launching browser and loading AWS Calculator.
        
        Args:
            resources: List of AWS resources to price
            screenshot_path: Optional path to save screenshot of the estimate
            debug_dir: Directory to save debug information
            
        Returns:
            Dictionary with pricing details
        """
        # Generate calculator URL with resources
        calculator_url = self.web_calculator.generate_calculator_url(resources)
        logger.info(f"Generated calculator URL: {calculator_url[:100]}...")
        
        # Launch browser
        browser = await self._launch_browser()
        page = await browser.newPage()
        
        try:
            # Set viewport to ensure all elements are visible
            await page.setViewport({'width': 1920, 'height': 1080})
            
            # Navigate to the calculator URL
            logger.info(f"Navigating to calculator")
            response = await page.goto(calculator_url, {'waitUntil': 'networkidle2', 'timeout': self.timeout})
            
            if not response.ok:
                logger.warning(f"Page load returned status: {response.status} {response.statusText}")
            
            # Capture debug info early on
            if self.debug or debug_dir:
                debug_output = debug_dir or os.path.dirname(screenshot_path or ".")
                await self._debug_page_structure(page, debug_output)
            
            # Wait for header to appear first as a sign the page is loading
            header = await self._wait_for_selector(page, self.SELECTORS['header'])
            if not header:
                logger.warning("Header not found, page may not be loading correctly")
                
                # Try going to the base calculator instead
                logger.info("Trying to go to base calculator URL")
                await page.goto(self.CALCULATOR_URL, {'waitUntil': 'networkidle2', 'timeout': self.timeout})
                
                # Wait for the header again
                header = await self._wait_for_selector(page, self.SELECTORS['header'])
                if not header:
                    raise Exception("AWS Calculator page failed to load properly")
                
                # If we made it here, we need to add services manually
                for resource in resources:
                    await self._add_service_manually(page, resource)
            
            # Wait for the pricing to fully load
            logger.info("Waiting for pricing to fully load")
            loading_finished = await self._wait_for_selector(page, self.SELECTORS['loading_finished'])
            if not loading_finished:
                logger.warning("Loading indicator not found, proceeding anyway")
                
            # Wait a bit longer for calculations to complete
            await asyncio.sleep(5)
            
            # Take screenshot of the current page state regardless of success
            if screenshot_path:
                screenshot_dir = os.path.dirname(screenshot_path)
                if screenshot_dir:
                    os.makedirs(screenshot_dir, exist_ok=True)
                    
                logger.info(f"Taking screenshot: {screenshot_path}")
                await page.screenshot({'path': screenshot_path, 'fullPage': True})
            
            # Extract pricing information
            logger.info("Extracting pricing information")
            pricing_data = await page.evaluate('''() => {
                const prices = {};
                
                // Try to get total price
                try {
                    const totalSelectors = [
                        '.calculator-grand-total', 
                        '.calculator-price', 
                        '.cost-display',
                        '[data-testid="total-price"]'
                    ];
                    
                    let totalPriceElement = null;
                    for (const selector of totalSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            totalPriceElement = element;
                            break;
                        }
                    }
                    
                    if (totalPriceElement) {
                        const priceText = totalPriceElement.textContent.trim();
                        const priceMatch = priceText.match(/\\$(\\d+([,\\.]\\d+)*)/);
                        prices.totalMonthly = priceMatch ? 
                            parseFloat(priceMatch[1].replace(/,/g, '')) : 0;
                        prices.rawTotal = priceText;
                    } else {
                        prices.totalMonthly = 0;
                        prices.rawTotal = "No total found";
                    }
                } catch (e) {
                    prices.totalMonthly = 0;
                    prices.totalError = e.toString();
                }
                
                // Try to extract service information
                try {
                    const services = [];
                    const serviceSelectors = [
                        '.service-calculation-container', 
                        '.service-row',
                        '[data-testid*="service-row"]'
                    ];
                    
                    let serviceRows = [];
                    for (const selector of serviceSelectors) {
                        const rows = document.querySelectorAll(selector);
                        if (rows && rows.length > 0) {
                            serviceRows = rows;
                            break;
                        }
                    }
                    
                    serviceRows.forEach(row => {
                        try {
                            // Try various selectors for service name and price
                            const nameSelectors = [
                                '.service-title', 
                                '.service-name',
                                '[data-testid*="service-name"]'
                            ];
                            const priceSelectors = [
                                '.service-total-value', 
                                '.service-price',
                                '[data-testid*="service-price"]'
                            ];
                            
                            let nameElement = null;
                            for (const selector of nameSelectors) {
                                const element = row.querySelector(selector);
                                if (element) {
                                    nameElement = element;
                                    break;
                                }
                            }
                            
                            let priceElement = null;
                            for (const selector of priceSelectors) {
                                const element = row.querySelector(selector);
                                if (element) {
                                    priceElement = element;
                                    break;
                                }
                            }
                            
                            if (nameElement && priceElement) {
                                const name = nameElement.textContent.trim();
                                const priceText = priceElement.textContent.trim();
                                const priceMatch = priceText.match(/\\$(\\d+([,\\.]\\d+)*)/);
                                const price = priceMatch ? 
                                    parseFloat(priceMatch[1].replace(/,/g, '')) : 0;
                                
                                services.push({ 
                                    name, 
                                    price,
                                    rawPrice: priceText 
                                });
                            } else if (nameElement) {
                                services.push({
                                    name: nameElement.textContent.trim(),
                                    price: 0,
                                    rawPrice: "No price found"
                                });
                            }
                        } catch (e) {
                            services.push({
                                name: 'Error parsing service',
                                price: 0,
                                error: e.toString()
                            });
                        }
                    });
                    
                    prices.services = services;
                } catch (e) {
                    prices.services = [];
                    prices.servicesError = e.toString();
                }
                
                return prices;
            }''')
            
            return {
                'status': 'success',
                'total_monthly_cost': pricing_data.get('totalMonthly', 0),
                'raw_total': pricing_data.get('rawTotal', ''),
                'services': pricing_data.get('services', []),
                'calculator_url': calculator_url
            }
            
        except Exception as e:
            logger.error(f"Error in browser calculator: {str(e)}")
            
            # Take error screenshot if path was provided
            if screenshot_path:
                error_screenshot_path = screenshot_path.replace('.png', '_error.png')
                try:
                    screenshot_dir = os.path.dirname(error_screenshot_path)
                    if screenshot_dir:
                        os.makedirs(screenshot_dir, exist_ok=True)
                    await page.screenshot({'path': error_screenshot_path, 'fullPage': True})
                    logger.info(f"Error screenshot saved to: {error_screenshot_path}")
                except Exception as screenshot_error:
                    logger.error(f"Failed to take error screenshot: {str(screenshot_error)}")
            
            return {
                'status': 'error',
                'message': f"Error accessing AWS Calculator: {str(e)}",
                'calculator_url': calculator_url
            }
            
        finally:
            await browser.close()
    
    async def save_price_estimate(self, 
                               resources: List[ResourceConfig],
                               output_dir: str,
                               debug: bool = False) -> Dict[str, Any]:
        """
        Save complete price estimate with screenshot to the specified directory.
        
        Args:
            resources: List of AWS resources to price
            output_dir: Directory to save outputs
            debug: Enable debugging output
            
        Returns:
            Dictionary with result details
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare file paths
        screenshot_path = os.path.join(output_dir, "aws_price_estimate.png")
        price_data_path = os.path.join(output_dir, "aws_price_data.json")
        url_path = os.path.join(output_dir, "aws_calculator_url.txt")
        
        # Set up debug directory if needed
        debug_dir = None
        if debug or self.debug:
            debug_dir = os.path.join(output_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)
        
        # Get price estimate
        result = await self.get_price_estimate(
            resources, 
            screenshot_path, 
            debug_dir=debug_dir
        )
        
        # Save calculator URL to file
        with open(url_path, "w") as f:
            f.write(result.get('calculator_url', ''))
        
        # Save price data to JSON
        if result['status'] == 'success':
            import json
            with open(price_data_path, "w") as f:
                json.dump(result, f, indent=2)
        
        return {
            **result,
            'screenshot_path': screenshot_path if result['status'] == 'success' else None,
            'price_data_path': price_data_path if result['status'] == 'success' else None,
            'url_path': url_path,
            'debug_dir': debug_dir
        }


def get_price_estimate(resources: List[ResourceConfig], 
                      screenshot_path: Optional[str] = None,
                      headless: bool = True,
                      timeout: int = 120000,
                      debug: bool = False) -> Dict[str, Any]:
    """
    Synchronous wrapper for getting price estimate.
    
    Args:
        resources: List of AWS resources to price
        screenshot_path: Optional path to save screenshot
        headless: Whether to run browser in headless mode
        timeout: Timeout in milliseconds
        debug: Enable debugging features
        
    Returns:
        Dictionary with pricing details
    """
    calculator = AWSBrowserCalculator(headless=headless, timeout=timeout, debug=debug)
    return asyncio.get_event_loop().run_until_complete(
        calculator.get_price_estimate(resources, screenshot_path)
    )


def save_price_estimate(resources: List[ResourceConfig], 
                       output_dir: str,
                       headless: bool = True,
                       timeout: int = 120000,
                       debug: bool = False) -> Dict[str, Any]:
    """
    Synchronous wrapper for saving price estimate.
    
    Args:
        resources: List of AWS resources to price
        output_dir: Directory to save outputs
        headless: Whether to run browser in headless mode
        timeout: Timeout in milliseconds
        debug: Enable debugging features
        
    Returns:
        Dictionary with result details
    """
    calculator = AWSBrowserCalculator(headless=headless, timeout=timeout, debug=debug)
    return asyncio.get_event_loop().run_until_complete(
        calculator.save_price_estimate(resources, output_dir, debug)
    ) 