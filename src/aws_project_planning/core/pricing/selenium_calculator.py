"""Selenium-based AWS Calculator interaction."""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import base64
import urllib.parse
import io
from PIL import Image

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import boto3

from .web_calculator import AWSWebCalculator
from .calculator import ResourceConfig

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AWSSeleniumCalculator:
    """
    Selenium-based AWS Calculator interaction.
    
    This service uses Selenium WebDriver to interact with the 
    AWS Pricing Calculator web interface for accurate pricing.
    It can either load a pre-configured estimate via URL or
    build an estimate by adding services manually.
    """
    
    # AWS Calculator URLs
    BASE_URL = "https://calculator.aws"
    CALCULATOR_URL = f"{BASE_URL}/#/estimate"
    
    # Selectors for AWS Calculator UI elements - these may need updating as the UI changes
    SELECTORS = {
        # Page navigation
        'create_estimate_button': ".awsui_content_vjswe_lssc8_153, button.awsui-button, button:contains('Create estimate')",
        'add_service_button': "[data-testid='add-service-button'], button.estimator__add-service-button, button:contains('Add service')",
        
        # Service selection
        'search_input': "#formField1094-1742393309755-2435, input[placeholder*='Search'], [data-testid='search-box']",
        'service_result': ".awsui-select-option, [data-testid='service-option']",
        'service_config_save': "button:contains('Add to my estimate'), button:contains('Save'), [data-testid='save-button']",

        # Service configuration - EC2
        'ec2_instance_type': "select[name='instanceType'], [data-testid='instance-type-dropdown']",
        'ec2_quantity': "input[name='quantity'], [data-testid='quantity-input']",
        
        # Service configuration - RDS
        'rds_engine': "select[name='engine'], [data-testid='engine-dropdown']",
        'rds_instance_type': "select[name='instanceType'], [data-testid='instance-type-dropdown']",
        'rds_storage': "input[name='storage'], [data-testid='storage-input']",
        
        # Service configuration - S3
        's3_storage': "input[name='storage'], [data-testid='storage-input']",
        
        # Results
        'service_rows': ".service-calculation-container, .service-row, [data-testid='service-row']",
        'service_name': ".service-title, .service-name, [data-testid='service-name']",
        'service_price': ".service-total-value, .service-price, [data-testid='service-price']",
        'total_price': ".calculator-grand-total, .calculator-price, [data-testid='total-price']"
    }
    
    def __init__(self, headless: bool = True, timeout: int = 60, debug: bool = False):
        """
        Initialize Selenium calculator.
        
        Args:
            headless: Whether to run browser in headless mode
            timeout: Default timeout in seconds for browser operations
            debug: Enable extra debugging features
        """
        self.headless = headless
        self.timeout = timeout
        self.debug = debug
        self.web_calculator = AWSWebCalculator()
        self.driver = None
        
        # Initialize AWS Bedrock client
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
    def _setup_driver(self):
        """
        Set up and configure the Chrome WebDriver.
        
        Returns:
            Configured WebDriver instance
        """
        chrome_options = ChromeOptions()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            
        # Common options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Set up debug options if requested
        if self.debug:
            chrome_options.add_argument("--auto-open-devtools-for-tabs")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Install the appropriate ChromeDriver version automatically
        try:
            driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=chrome_options
            )
            driver.set_window_size(1920, 1080)
            
            # Set default timeout for finding elements
            driver.implicitly_wait(10)
            
            return driver
        except Exception as e:
            logger.error(f"Error setting up Chrome WebDriver: {str(e)}")
            raise
    
    def _wait_for_element(self, selector, timeout=None, wait_type="visible"):
        """
        Wait for an element to be visible, clickable, or present.
        
        Args:
            selector: CSS selector
            timeout: Timeout in seconds (or use default)
            wait_type: 'visible', 'clickable', or 'present'
            
        Returns:
            WebElement if found, None otherwise
        """
        if not timeout:
            timeout = self.timeout
            
        # Handle :contains() in selectors
        if ":contains(" in selector:
            text = selector.split(":contains(")[1].split(")")[0].strip("'\"")
            base_selector = selector.split(":contains(")[0].strip()
            
            # Create a custom expected condition for finding elements with text
            def find_element_containing_text(driver):
                try:
                    if base_selector:
                        elements = driver.find_elements(By.CSS_SELECTOR, base_selector)
                        for element in elements:
                            if text.lower() in element.text.lower():
                                if wait_type == "visible" and not element.is_displayed():
                                    continue
                                return element
                    return None
                except:
                    return None
            
            # Wait with custom condition
            try:
                wait = WebDriverWait(self.driver, timeout)
                return wait.until(find_element_containing_text)
            except TimeoutException:
                logger.warning(f"Timeout waiting for element with text: {text}")
                return None
            
        # Try all possible By methods
        by_methods = [
            (By.CSS_SELECTOR, selector),
            (By.XPATH, f"//*[contains(text(), '{selector}')]") if not selector.startswith('.') and not selector.startswith('#') and not selector.startswith('[') else None,
            (By.ID, selector) if not selector.startswith('.') and not selector.startswith('#') and not selector.startswith('[') else None
        ]
        
        # Filter out None values
        by_methods = [method for method in by_methods if method]
        
        wait = WebDriverWait(self.driver, timeout)
        
        for by_method, selector_value in by_methods:
            try:
                if wait_type == "clickable":
                    return wait.until(EC.element_to_be_clickable((by_method, selector_value)))
                elif wait_type == "present":
                    return wait.until(EC.presence_of_element_located((by_method, selector_value)))
                else:  # Default to visible
                    return wait.until(EC.visibility_of_element_located((by_method, selector_value)))
            except (TimeoutException, NoSuchElementException):
                continue
                
        # If we reach here, no method worked
        logger.warning(f"Could not find element with selector: {selector}")
        return None
    
    def _find_element(self, selector):
        """
        Find an element using multiple strategies.
        
        Args:
            selector: CSS selector or text to find
            
        Returns:
            WebElement if found, None otherwise
        """
        # Try as CSS selector first (without the :contains part)
        clean_selector = selector
        if ":contains(" in clean_selector:
            clean_selector = clean_selector.split(":contains(")[0].strip()
            
        try:
            if clean_selector:
                return self.driver.find_element(By.CSS_SELECTOR, clean_selector)
        except NoSuchElementException:
            pass
            
        # Try looking for elements containing the text
        if ":contains(" in selector:
            try:
                # Extract the text from :contains('text')
                text = selector.split(":contains(")[1].split(")")[0].strip("'\"")
                xpath = f"//*[contains(text(), '{text}')]"
                return self.driver.find_element(By.XPATH, xpath)
            except (NoSuchElementException, IndexError):
                pass
                
        # Try as XPath containing text (if it looks like plain text)
        if not selector.startswith('.') and not selector.startswith('#') and not selector.startswith('['):
            try:
                return self.driver.find_element(By.XPATH, f"//*[contains(text(), '{selector}')]")
            except NoSuchElementException:
                pass
                
        # Try as ID if it's not a CSS selector
        if not selector.startswith('.') and not selector.startswith('#') and not selector.startswith('['):
            try:
                return self.driver.find_element(By.ID, selector)
            except NoSuchElementException:
                pass
                
        return None
    
    def _safe_click(self, selector, timeout=None):
        """
        Safely click an element with fallbacks.
        
        Args:
            selector: CSS selector or text to match
            timeout: Timeout in seconds
            
        Returns:
            True if click was successful, False otherwise
        """
        # Handle :contains() in the selector
        if ":contains(" in selector:
            text = selector.split(":contains(")[1].split(")")[0].strip("'\"")
            base_selector = selector.split(":contains(")[0].strip()
            
            # Try to find elements that match the base selector
            try:
                if base_selector:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, base_selector)
                    for element in elements:
                        if text.lower() in element.text.lower():
                            try:
                                element.click()
                                logger.info(f"Clicked element containing text: {text}")
                                return True
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    logger.info(f"Clicked element with JavaScript containing text: {text}")
                                    return True
                                except:
                                    continue
            except Exception as e:
                logger.warning(f"Failed to click using base selector and text: {str(e)}")
        
        # Fall back to normal element waiting and clicking
        element = self._wait_for_element(selector, timeout, wait_type="clickable")
        if not element:
            logger.warning(f"Element not found/clickable: {selector}")
            
            # Try finding any button or link with matching text as last resort
            if not selector.startswith('.') and not selector.startswith('#') and not selector.startswith('['):
                try:
                    xpath = f"//button[contains(text(), '{selector}')] | //a[contains(text(), '{selector}')]"
                    element = self.driver.find_element(By.XPATH, xpath)
                    element.click()
                    logger.info(f"Clicked element with text using XPath: {selector}")
                    return True
                except:
                    pass
                    
            return False
            
        try:
            element.click()
            logger.info(f"Clicked: {selector}")
            return True
        except Exception as e:
            logger.warning(f"Normal click failed on {selector}, trying JavaScript: {str(e)}")
            
            try:
                # Try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                logger.info(f"Clicked with JavaScript: {selector}")
                return True
            except Exception as e:
                logger.error(f"JavaScript click also failed: {str(e)}")
                return False
    
    def _take_screenshot(self, path):
        """
        Take a screenshot of the current page.
        
        Args:
            path: Path to save the screenshot
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Take screenshot
            self.driver.save_screenshot(path)
            logger.info(f"Screenshot saved to: {path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
    
    def _save_page_source(self, path):
        """
        Save the current page HTML source.
        
        Args:
            path: Path to save the HTML
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Save page source
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
                
            logger.info(f"Page source saved to: {path}")
        except Exception as e:
            logger.error(f"Failed to save page source: {str(e)}")
    
    def _debug_page(self, output_dir):
        """
        Save debugging information about the current page.
        
        Args:
            output_dir: Directory to save debug files
        """
        if not self.debug:
            return
            
        # Create debug directory
        debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Take screenshot
        self._take_screenshot(os.path.join(debug_dir, "debug_screenshot.png"))
        
        # Save page source
        self._save_page_source(os.path.join(debug_dir, "page_source.html"))
        
        # Extract and save element information
        try:
            # Get all buttons
            buttons = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('button')).map(btn => ({
                    text: btn.textContent.trim(),
                    id: btn.id,
                    classes: btn.className,
                    disabled: btn.disabled,
                    visible: btn.offsetParent !== null
                }));
            """)
            
            # Get key page elements
            elements = self.driver.execute_script("""
                return {
                    inputs: Array.from(document.querySelectorAll('input')).map(el => ({
                        type: el.type,
                        id: el.id,
                        name: el.name,
                        placeholder: el.placeholder,
                        value: el.value
                    })),
                    selects: Array.from(document.querySelectorAll('select')).map(el => ({
                        id: el.id,
                        name: el.name,
                        options: Array.from(el.options).map(opt => opt.textContent.trim())
                    })),
                    links: Array.from(document.querySelectorAll('a')).map(el => ({
                        text: el.textContent.trim(),
                        href: el.href
                    })).filter(link => link.text)
                };
            """)
            
            # Save the element info to JSON
            with open(os.path.join(debug_dir, "page_elements.json"), 'w', encoding='utf-8') as f:
                json.dump({
                    "buttons": buttons,
                    "elements": elements
                }, f, indent=2)
                
            logger.info(f"Page elements information saved to {debug_dir}")
            
        except Exception as e:
            logger.error(f"Failed to extract page elements: {str(e)}")
    
    def _add_service_manually(self, resource: ResourceConfig):
        """
        Add a service manually through the AWS Calculator UI.
        
        Args:
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
            # Click "Add service" button
            if not self._safe_click(self.SELECTORS['add_service_button']):
                logger.error("Could not click 'Add service' button")
                if self.debug:
                    self._debug_page("add_service_failed")
                return False
                
            # Wait for search input and enter service name
            search_input = self._wait_for_element(self.SELECTORS['search_input'])
            if not search_input:
                logger.error("Could not find service search input")
                return False
                
            search_input.clear()
            search_input.send_keys(aws_service_name)
            time.sleep(1)  # Wait for search results
            
            # Find and click the service in search results
            service_selector = f"{self.SELECTORS['service_result']}:contains('{aws_service_name}')"
            if not self._safe_click(service_selector):
                # Try generic selector if specific one fails
                if not self._safe_click(self.SELECTORS['service_result']):
                    logger.error(f"Could not select {aws_service_name} service")
                    return False
                else:
                    # JavaScript click as a fallback
                    try:
                        element = self._find_element(self.SELECTORS['service_result'])
                        self.driver.execute_script("arguments[0].click();", element)
                        logger.info(f"Clicked {aws_service_name} service with JavaScript")
                    except Exception as e:
                        logger.error(f"JavaScript click failed for {aws_service_name} service: {str(e)}")
                        return False
            
            # Click the 'Configure' button for the EC2 service
            configure_button_selector = ".awsui_content_vjswe_lssc8_153.awsui_label_1f1d4_ocied_5, button:contains('Configure'), [data-testid='configure-button']"
            if not self._safe_click(configure_button_selector):
                logger.error("Could not click 'Configure' button for EC2 service")
                return False
            
            # Configure the service based on its type
            if resource.service == "ec2":
                success = self._configure_ec2(resource)
            elif resource.service == "rds":
                success = self._configure_rds(resource)
            elif resource.service == "s3":
                success = self._configure_s3(resource)
            else:
                logger.warning(f"No specific configuration method for {resource.service}")
                success = True  # Assume default configuration is OK
                
            if not success:
                logger.error(f"Failed to configure {resource.service}")
                return False
                
            # Wait and click the "Add to my estimate" button
            time.sleep(1)
            if not self._safe_click(self.SELECTORS['service_config_save']):
                logger.error("Could not save service configuration")
                return False
                
            # Wait for the service to be added to the estimate
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Error adding service manually: {str(e)}")
            return False
    
    def _configure_ec2(self, resource: ResourceConfig):
        """
        Configure EC2 instance in the AWS Calculator.
        
        Args:
            resource: Resource configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get instance type from specs
            instance_type = resource.specs.get("instance_type", "t3.medium")
            quantity = resource.quantity
            
            # Wait for instance type selector
            instance_type_select = self._wait_for_element(self.SELECTORS['ec2_instance_type'])
            if not instance_type_select:
                logger.error("Could not find EC2 instance type selector")
                return False
                
            # Select instance type
            instance_type_select.click()
            instance_option = self._wait_for_element(f"option[value='{instance_type}'], option:contains('{instance_type}')")
            if instance_option:
                instance_option.click()
            else:
                logger.warning(f"Could not find instance type: {instance_type}")
                
            # Set quantity if specified
            if quantity > 1:
                quantity_input = self._wait_for_element(self.SELECTORS['ec2_quantity'])
                if quantity_input:
                    quantity_input.clear()
                    quantity_input.send_keys(str(quantity))
                    
            return True
            
        except Exception as e:
            logger.error(f"Error configuring EC2: {str(e)}")
            return False
    
    def _configure_rds(self, resource: ResourceConfig):
        """
        Configure RDS instance in the AWS Calculator.
        
        Args:
            resource: Resource configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get RDS specifications
            engine = resource.specs.get("engine", "mysql")
            instance_type = resource.specs.get("instance_type", "db.t3.medium")
            storage_gb = resource.specs.get("storage_gb", 100)
            
            # Select database engine
            engine_select = self._wait_for_element(self.SELECTORS['rds_engine'])
            if engine_select:
                engine_select.click()
                engine_option = self._wait_for_element(f"option[value='{engine}'], option:contains('{engine}')")
                if engine_option:
                    engine_option.click()
            
            # Select instance type
            instance_type_select = self._wait_for_element(self.SELECTORS['rds_instance_type'])
            if instance_type_select:
                instance_type_select.click()
                instance_option = self._wait_for_element(f"option[value='{instance_type}'], option:contains('{instance_type}')")
                if instance_option:
                    instance_option.click()
            
            # Set storage size
            storage_input = self._wait_for_element(self.SELECTORS['rds_storage'])
            if storage_input:
                storage_input.clear()
                storage_input.send_keys(str(storage_gb))
                
            return True
            
        except Exception as e:
            logger.error(f"Error configuring RDS: {str(e)}")
            return False
    
    def _configure_s3(self, resource: ResourceConfig):
        """
        Configure S3 storage in the AWS Calculator.
        
        Args:
            resource: Resource configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get S3 specifications
            storage_gb = resource.specs.get("storage_gb", 100)
            
            # Set storage size
            storage_input = self._wait_for_element(self.SELECTORS['s3_storage'])
            if storage_input:
                storage_input.clear()
                storage_input.send_keys(str(storage_gb))
                
            return True
            
        except Exception as e:
            logger.error(f"Error configuring S3: {str(e)}")
            return False
    
    def _extract_price_data(self):
        """
        Extract pricing information from the AWS Calculator page.
        
        Returns:
            Dictionary with pricing details
        """
        try:
            # Wait for elements to be visible
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, self.SELECTORS['total_price']))
            )
            
            # Extract total price
            total_price_element = self._find_element(self.SELECTORS['total_price'])
            total_price_text = total_price_element.text if total_price_element else "0"
            total_price = 0
            
            # Parse the price from text (e.g., "$123.45" -> 123.45)
            import re
            price_match = re.search(r'\$([\d,]+\.\d+|\d+)', total_price_text)
            if price_match:
                total_price = float(price_match.group(1).replace(',', ''))
            
            # Extract individual service costs
            services = []
            service_rows = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['service_rows'])
            
            for row in service_rows:
                try:
                    name_element = row.find_element(By.CSS_SELECTOR, self.SELECTORS['service_name'])
                    price_element = row.find_element(By.CSS_SELECTOR, self.SELECTORS['service_price'])
                    
                    name = name_element.text.strip()
                    price_text = price_element.text.strip()
                    
                    price = 0
                    price_match = re.search(r'\$([\d,]+\.\d+|\d+)', price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                    
                    services.append({
                        'name': name,
                        'price': price,
                        'raw_price': price_text
                    })
                except Exception as e:
                    logger.warning(f"Error extracting service data: {str(e)}")
            
            return {
                'total_monthly_cost': total_price,
                'raw_total': total_price_text,
                'services': services
            }
            
        except Exception as e:
            logger.error(f"Error extracting price data: {str(e)}")
            return {
                'total_monthly_cost': 0,
                'raw_total': 'Error extracting data',
                'services': []
            }
    
    def _analyze_page_with_llm(self, html_content, screenshot=None, current_state=None, resource=None):
        """
        Analyze the page HTML content using AWS Bedrock to determine next actions.
        
        Args:
            html_content: The HTML content of the page
            screenshot: Optional base64 encoded screenshot of the current page
            current_state: Current state of the interaction (what we're trying to do)
            resource: Optional resource configuration we're trying to add
            
        Returns:
            A dictionary with actions to take
        """
        try:
            # Take a screenshot of the current page
            if screenshot is None:
                # Take screenshot and save to a temporary file
                temp_screenshot_path = f"temp_screenshot_{int(time.time())}.png"
                self.driver.save_screenshot(temp_screenshot_path)
                
                # Convert to base64 if needed
                with open(temp_screenshot_path, "rb") as img_file:
                    screenshot = base64.b64encode(img_file.read()).decode('utf-8')
                    
                # Clean up temporary file
                try:
                    os.remove(temp_screenshot_path)
                except:
                    pass
            
            # Create a prompt for the LLM
            prompt = self._create_llm_prompt(html_content, screenshot, current_state, resource)
            
            # Send to AWS Bedrock
            response = self.bedrock_client.invoke_model(
                modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ]
                })
            )
            
            # Parse the response
            response_body = json.loads(response['body'].read())
            llm_response_text = response_body['content'][0]['text']
            
            # Parse the LLM's response into actions
            actions = self._parse_llm_response(llm_response_text)
            
            logger.info(f"LLM suggested actions: {actions}")
            return actions
            
        except Exception as e:
            logger.error(f"Error analyzing page with AWS Bedrock: {str(e)}")
            # Return a safe default action
            return {'action': 'error', 'message': str(e)}
    
    def _create_llm_prompt(self, html_content, screenshot, current_state, resource):
        """Create a prompt for the LLM based on the current state."""
        # Extract key elements from the page for a more concise prompt
        buttons = self.driver.execute_script("""
            return Array.from(document.querySelectorAll('button')).map(btn => ({
                text: btn.textContent.trim(),
                id: btn.id,
                classes: btn.className,
                disabled: btn.disabled,
                visible: btn.offsetParent !== null
            })).filter(btn => btn.text && btn.visible);
        """)
        
        inputs = self.driver.execute_script("""
            return Array.from(document.querySelectorAll('input')).map(input => ({
                type: input.type,
                id: input.id,
                name: input.name,
                placeholder: input.placeholder,
                value: input.value,
                visible: input.offsetParent !== null
            })).filter(input => input.visible);
        """)
        
        selects = self.driver.execute_script("""
            return Array.from(document.querySelectorAll('select')).map(select => ({
                id: select.id,
                name: select.name,
                options: Array.from(select.options).map(opt => opt.textContent.trim()),
                visible: select.offsetParent !== null
            })).filter(select => select.visible);
        """)
        
        # Create the base prompt
        base_prompt = f"""
        You are an AI assistant that helps navigate and interact with the AWS Pricing Calculator.
        
        Current state: {current_state or "Initial page load"}
        
        I'm going to show you the current state of the AWS Calculator interface.
        Your task is to analyze this information and tell me what actions to take next to {current_state or "add services to the calculator"}.
        
        Here are the visible buttons on the page:
        {json.dumps(buttons, indent=2)}
        
        Here are the visible input fields:
        {json.dumps(inputs, indent=2)}
        
        Here are the visible dropdown menus:
        {json.dumps(selects, indent=2)}
        """
        
        # Add resource information if available
        if resource:
            resource_info = f"""
            I'm trying to add the following resource:
            Service: {resource.service}
            Quantity: {resource.quantity}
            Specifications: {json.dumps(resource.specs, indent=2)}
            """
            base_prompt += resource_info
        
        # Add instructions for the response format
        instructions = """
        Please respond with specific actions to take in this JSON format:
        
        {
            "action": "[click|input|select|wait|complete]",
            "selector": "CSS selector or element identifier",
            "value": "Value to input or select (if applicable)",
            "explanation": "Why this action is needed",
            "next_state": "Description of what state we'll be in after this action"
        }
        
        If the action is 'click', provide the selector for the element to click.
        If the action is 'input', provide the selector and the value to input.
        If the action is 'select', provide the selector and the option to select.
        If the action is 'wait', provide the time in seconds.
        If the action is 'complete', it means the current task is done.
        
        For example:
        {
            "action": "click",
            "selector": "button:contains('Add service')",
            "explanation": "Click the 'Add service' button to start adding a new service",
            "next_state": "Service selection page"
        }
        
        Be precise and focus on the most important action to take next.
        """
        
        return base_prompt + instructions
    
    def _parse_llm_response(self, llm_response_text):
        """Parse the LLM's response text into a structured action."""
        try:
            # Extract JSON from the LLM's response
            import re
            json_match = re.search(r'({[\s\S]*})', llm_response_text)
            
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # If no JSON is found, try to extract key information in a best-effort way
                action_match = re.search(r'action["\s:]+([^,"]+)', llm_response_text)
                selector_match = re.search(r'selector["\s:]+([^,"]+)', llm_response_text)
                
                action = action_match.group(1) if action_match else "error"
                selector = selector_match.group(1) if selector_match else ""
                
                return {
                    "action": action,
                    "selector": selector,
                    "explanation": "Extracted from non-JSON response",
                    "next_state": "Unknown"
                }
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {
                "action": "error",
                "explanation": f"Could not parse LLM response: {str(e)}",
                "message": llm_response_text
            }
    
    def _execute_llm_action(self, action):
        """Execute an action based on the LLM's analysis."""
        try:
            if action.get('action') == 'click':
                selector = action.get('selector', '')
                if selector:
                    success = self._safe_click(selector)
                    if not success:
                        logger.warning(f"Click action failed for selector: {selector}")
                    return success
                return False
                
            elif action.get('action') == 'input':
                selector = action.get('selector', '')
                value = action.get('value', '')
                if selector and value:
                    element = self._wait_for_element(selector)
                    if element:
                        element.clear()
                        element.send_keys(value)
                        logger.info(f"Input '{value}' into {selector}")
                        return True
                logger.warning(f"Input action failed for selector: {selector}")
                return False
                
            elif action.get('action') == 'select':
                selector = action.get('selector', '')
                value = action.get('value', '')
                if selector and value:
                    element = self._wait_for_element(selector)
                    if element:
                        element.click()
                        option_selector = f"option:contains('{value}')"
                        option = self._wait_for_element(option_selector)
                        if option:
                            option.click()
                            logger.info(f"Selected '{value}' from {selector}")
                            return True
                logger.warning(f"Select action failed for selector: {selector}")
                return False
                
            elif action.get('action') == 'wait':
                wait_time = float(action.get('value', 1))
                logger.info(f"Waiting for {wait_time} seconds")
                time.sleep(wait_time)
                return True
                
            elif action.get('action') == 'complete':
                logger.info(f"Task completed: {action.get('explanation', '')}")
                return True
                
            else:
                logger.warning(f"Unknown action: {action.get('action')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            return False

    def _add_service_manually_with_llm(self, resource):
        """
        Add a service manually through the AWS Calculator UI using LLM guidance.
        
        Args:
            resource: Resource configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if Bedrock is accessible
            try:
                # Test Bedrock access with a simple prompt
                self.bedrock_client.invoke_model(
                    modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "test"}]
                    })
                )
                use_llm = True
            except Exception as e:
                logger.warning(f"AWS Bedrock not accessible, falling back to manual addition: {str(e)}")
                use_llm = False

            # If Bedrock isn't accessible, use the traditional manual approach
            if not use_llm:
                return self._add_service_manually(resource)
                
            # Initial state
            current_state = f"Adding {resource.service} service"
            
            # Loop until the service is added or we fail
            max_iterations = 15
            iterations = 0
            
            while iterations < max_iterations:
                iterations += 1
                
                # Get HTML and analyze with LLM
                html_content = self.driver.page_source
                actions = self._analyze_page_with_llm(
                    html_content=html_content,
                    current_state=current_state,
                    resource=resource
                )
                
                # Check for completion or error
                if actions.get('action') == 'complete':
                    logger.info(f"Successfully added {resource.service} service")
                    return True
                    
                if actions.get('action') == 'error':
                    logger.error(f"Error adding {resource.service} service: {actions.get('message')}")
                    return False
                
                # Execute the suggested action
                success = self._execute_llm_action(actions)
                
                if not success:
                    logger.warning(f"Failed to execute action: {actions}")
                    # Take screenshot for debugging
                    if self.debug:
                        debug_path = f"llm_action_failed_{iterations}.png"
                        self._take_screenshot(debug_path)
                    
                    # If we fail to execute an action, try again with a different approach
                    current_state += " (previous action failed)"
                else:
                    # Update the current state
                    current_state = actions.get('next_state', current_state)
                
                # Wait a moment for page to update
                time.sleep(2)
            
            logger.error(f"Failed to add {resource.service} service after {max_iterations} iterations")
            return False
            
        except Exception as e:
            logger.error(f"Error in agentic service addition: {str(e)}")
            # Fall back to manual addition
            logger.info(f"Falling back to manual addition for {resource.service}")
            return self._add_service_manually(resource)

    def get_price_estimate(self, 
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
        
        # Set up the driver
        self.driver = self._setup_driver()
        
        try:
            # Navigate to calculator
            logger.info("Navigating to AWS Calculator...")
            self.driver.get(calculator_url)
            time.sleep(3)  # Wait for page to initialize
            
            if debug_dir:
                self._debug_page(debug_dir)
            
            # Check if we need to add services manually
            try:
                # Try to locate the total price element to see if our estimate loaded
                total_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.SELECTORS['total_price']))
                )
                logger.info("Calculator loaded from URL successfully")
            except TimeoutException:
                logger.warning("Could not detect price information, using LLM to add services manually")
                
                # Add each service using the LLM-guided approach
                for resource in resources:
                    logger.info(f"Adding {resource.service} service using LLM guidance...")
                    success = self._add_service_manually_with_llm(resource)
                    if not success:
                        logger.error(f"Failed to add {resource.service} - taking error screenshot")
                        # Save error screenshot
                        if screenshot_path:
                            error_path = screenshot_path.replace('.png', f'_{resource.service}_error.png')
                            self._take_screenshot(error_path)
                    time.sleep(2)
            
            # Wait for pricing to be calculated
            time.sleep(5)
            
            # Take screenshot if requested
            if screenshot_path:
                screenshot_dir = os.path.dirname(screenshot_path)
                if screenshot_dir:
                    os.makedirs(screenshot_dir, exist_ok=True)
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved to: {screenshot_path}")
            
            # Extract pricing information
            logger.info("Extracting pricing information...")
            pricing_data = self._extract_price_data()
            
            return {
                'status': 'success',
                'total_monthly_cost': pricing_data.get('total_monthly_cost', 0),
                'raw_total': pricing_data.get('raw_total', ''),
                'services': pricing_data.get('services', []),
                'calculator_url': calculator_url
            }
            
        except Exception as e:
            logger.error(f"Error in Selenium calculator: {str(e)}")
            
            # Take error screenshot
            if screenshot_path:
                error_screenshot_path = screenshot_path.replace('.png', '_error.png')
                try:
                    screenshot_dir = os.path.dirname(error_screenshot_path)
                    if screenshot_dir:
                        os.makedirs(screenshot_dir, exist_ok=True)
                    self.driver.save_screenshot(error_screenshot_path)
                    logger.info(f"Error screenshot saved to: {error_screenshot_path}")
                except Exception:
                    pass
            
            return {
                'status': 'error',
                'message': f"Error accessing AWS Calculator: {str(e)}",
                'calculator_url': calculator_url
            }
            
        finally:
            # Quit the driver
            if not self.debug:
                self.driver.quit()
    
    def save_price_estimate(self, 
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
        error_screenshot_path = os.path.join(output_dir, "aws_price_estimate_error.png")
        price_data_path = os.path.join(output_dir, "aws_price_data.json")
        url_path = os.path.join(output_dir, "aws_calculator_url.txt")
        
        # Set up debug directory if needed
        debug_dir = None
        if debug or self.debug:
            debug_dir = os.path.join(output_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)
        
        try:
            # Get price estimate
            result = self.get_price_estimate(
                resources, 
                screenshot_path, 
                debug_dir=debug_dir
            )
            
            # Save calculator URL to file
            with open(url_path, "w") as f:
                f.write(result.get('calculator_url', ''))
            
            # Save price data to JSON
            if result['status'] == 'success':
                with open(price_data_path, "w") as f:
                    json.dump(result, f, indent=2)
            
            return {
                **result,
                'screenshot_path': screenshot_path if os.path.exists(screenshot_path) else None,
                'error_screenshot_path': error_screenshot_path if os.path.exists(error_screenshot_path) else None,
                'price_data_path': price_data_path if result['status'] == 'success' else None,
                'url_path': url_path,
                'debug_dir': debug_dir
            }
        except Exception as e:
            logger.error(f"Exception in save_price_estimate: {str(e)}")
            # Ensure we return appropriate values even on exception
            return {
                'status': 'error',
                'message': f"Error in save_price_estimate: {str(e)}",
                'screenshot_path': screenshot_path if os.path.exists(screenshot_path) else None,
                'error_screenshot_path': error_screenshot_path if os.path.exists(error_screenshot_path) else None,
                'url_path': url_path if os.path.exists(url_path) else None,
                'calculator_url': '',
                'debug_dir': debug_dir
            }


def get_price_estimate(resources: List[ResourceConfig], 
                     screenshot_path: Optional[str] = None,
                     headless: bool = True,
                     timeout: int = 60,
                     debug: bool = False) -> Dict[str, Any]:
    """
    Synchronous function for getting price estimate using Selenium.
    
    Args:
        resources: List of AWS resources to price
        screenshot_path: Optional path to save screenshot
        headless: Whether to run browser in headless mode
        timeout: Timeout in seconds
        debug: Enable debugging features
        
    Returns:
        Dictionary with pricing details
    """
    calculator = AWSSeleniumCalculator(headless=headless, timeout=timeout, debug=debug)
    return calculator.get_price_estimate(resources, screenshot_path)


def save_price_estimate(resources: List[ResourceConfig], 
                      output_dir: str,
                      headless: bool = True,
                      timeout: int = 60,
                      debug: bool = False) -> Dict[str, Any]:
    """
    Synchronous function for saving price estimate using Selenium.
    
    Args:
        resources: List of AWS resources to price
        output_dir: Directory to save outputs
        headless: Whether to run browser in headless mode
        timeout: Timeout in seconds
        debug: Enable debugging features
        
    Returns:
        Dictionary with result details
    """
    calculator = AWSSeleniumCalculator(headless=headless, timeout=timeout, debug=debug)
    return calculator.save_price_estimate(resources, output_dir, debug)


def load_selenium_script(script_path: str) -> Dict[str, Any]:
    """
    Load and parse a Selenium IDE script (.side file).
    
    Args:
        script_path: Path to .side file
        
    Returns:
        Dictionary with script metadata and commands
    """
    try:
        with open(script_path, 'r') as f:
            script_data = json.load(f)
            
        # Extract the first test's commands
        if script_data.get('tests') and len(script_data['tests']) > 0:
            first_test = script_data['tests'][0]
            commands = first_test.get('commands', [])
            
            return {
                'name': first_test.get('name', 'Unnamed Test'),
                'url': script_data.get('url', ''),
                'commands': commands
            }
        else:
            logger.error("No tests found in Selenium script")
            return {'name': 'Empty', 'url': '', 'commands': []}
            
    except Exception as e:
        logger.error(f"Error loading Selenium script: {str(e)}")
        return {'name': 'Error', 'url': '', 'commands': []} 