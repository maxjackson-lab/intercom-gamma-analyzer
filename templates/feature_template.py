"""
Template for new features in Intercom Analysis Tool.

This template includes:
- Comprehensive logging
- Error handling
- Type hints
- Docstrings
- Test structure

Copy this template and modify for your new feature.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import json

from config.settings import settings

logger = logging.getLogger(__name__)


class NewFeature:
    """
    Template for new features with comprehensive logging and error handling.
    
    This class demonstrates the required patterns for:
    - Logging at appropriate levels
    - Error handling with specific exceptions
    - Type hints for all methods
    - Comprehensive docstrings
    - Input validation
    
    Args:
        config: Configuration dictionary for the feature
        output_dir: Directory for output files (optional)
    """
    
    def __init__(self, config: Dict[str, Any], output_dir: Optional[Path] = None):
        """
        Initialize the feature with configuration and logging.
        
        Args:
            config: Configuration dictionary
            output_dir: Output directory for files
            
        Raises:
            ValueError: If required configuration is missing
        """
        self.config = config
        self.output_dir = output_dir or Path(settings.output_directory)
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        self._validate_config()
        
        # Create output directory if needed
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Initialized {self.__class__.__name__} with config keys: {list(config.keys())}")
        self.logger.debug(f"Output directory: {self.output_dir}")
    
    def _validate_config(self) -> None:
        """
        Validate the configuration dictionary.
        
        Raises:
            ValueError: If required configuration is missing
        """
        required_keys = ["required_setting"]  # Add your required keys here
        
        for key in required_keys:
            if key not in self.config:
                error_msg = f"Required configuration key '{key}' is missing"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        
        self.logger.debug("Configuration validation passed")
    
    def process_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process data with comprehensive logging and error handling.
        
        Args:
            data: List of data dictionaries to process
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ValueError: If data is empty or invalid
            ProcessingError: If processing fails
        """
        self.logger.info(f"Starting data processing for {len(data)} items")
        
        # Validate input
        if not data:
            error_msg = "Data list cannot be empty"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not isinstance(data, list):
            error_msg = f"Data must be a list, got {type(data)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Log processing start
            start_time = datetime.now()
            self.logger.debug(f"Processing started at {start_time}")
            
            # Perform processing
            results = self._do_processing(data)
            
            # Log processing completion
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Processing completed successfully in {duration:.2f} seconds")
            self.logger.info(f"Processed {len(data)} items, generated {len(results.get('output', []))} results")
            
            return results
            
        except ValueError as e:
            self.logger.error(f"Validation error during processing: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during processing: {e}", exc_info=True)
            raise ProcessingError(f"Failed to process data: {e}") from e
    
    async def async_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform async operation with logging and error handling.
        
        Args:
            input_data: Input data for the operation
            
        Returns:
            Operation results
            
        Raises:
            ValueError: If input data is invalid
            AsyncOperationError: If async operation fails
        """
        self.logger.info("Starting async operation")
        self.logger.debug(f"Input data keys: {list(input_data.keys())}")
        
        # Validate input
        if not input_data:
            error_msg = "Input data cannot be empty"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Log operation start
            start_time = datetime.now()
            
            # Perform async work
            result = await self._async_work(input_data)
            
            # Log operation completion
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Async operation completed successfully in {duration:.2f} seconds")
            self.logger.debug(f"Operation result keys: {list(result.keys())}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Async operation failed: {e}", exc_info=True)
            raise AsyncOperationError(f"Async operation failed: {e}") from e
    
    def _do_processing(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Internal processing method.
        
        Args:
            data: Data to process
            
        Returns:
            Processing results
        """
        self.logger.debug("Performing internal processing")
        
        # Add your processing logic here
        results = {
            "processed_count": len(data),
            "output": [],
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "config_used": self.config
            }
        }
        
        # Example processing
        for item in data:
            try:
                processed_item = self._process_single_item(item)
                results["output"].append(processed_item)
            except Exception as e:
                self.logger.warning(f"Failed to process item {item.get('id', 'unknown')}: {e}")
                # Continue processing other items
        
        self.logger.debug(f"Internal processing completed. Processed {len(results['output'])} items")
        return results
    
    async def _async_work(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal async work method.
        
        Args:
            input_data: Input data for async work
            
        Returns:
            Async work results
        """
        self.logger.debug("Performing internal async work")
        
        # Simulate async work
        await asyncio.sleep(0.1)  # Replace with actual async work
        
        # Add your async logic here
        results = {
            "async_result": "completed",
            "input_processed": input_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.debug("Internal async work completed")
        return results
    
    def _process_single_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single item.
        
        Args:
            item: Single item to process
            
        Returns:
            Processed item
            
        Raises:
            ProcessingError: If item processing fails
        """
        try:
            # Add your single item processing logic here
            processed_item = {
                "id": item.get("id", "unknown"),
                "processed": True,
                "original_data": item
            }
            
            return processed_item
            
        except Exception as e:
            self.logger.error(f"Failed to process single item: {e}")
            raise ProcessingError(f"Single item processing failed: {e}") from e
    
    def export_results(self, results: Dict[str, Any], filename: str) -> Path:
        """
        Export results to file with logging.
        
        Args:
            results: Results to export
            filename: Output filename
            
        Returns:
            Path to exported file
            
        Raises:
            ExportError: If export fails
        """
        self.logger.info(f"Exporting results to {filename}")
        
        try:
            output_path = self.output_dir / filename
            
            # Export based on file extension
            if filename.endswith('.json'):
                with open(output_path, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
            else:
                # Add other export formats as needed
                raise ValueError(f"Unsupported file format: {filename}")
            
            self.logger.info(f"Results exported successfully to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}", exc_info=True)
            raise ExportError(f"Failed to export results: {e}") from e
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the feature.
        
        Returns:
            Status information
        """
        status = {
            "feature_name": self.__class__.__name__,
            "config_keys": list(self.config.keys()),
            "output_directory": str(self.output_dir),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.debug(f"Status requested: {status}")
        return status


# Custom Exceptions
class ProcessingError(Exception):
    """Exception raised when data processing fails."""
    pass


class AsyncOperationError(Exception):
    """Exception raised when async operations fail."""
    pass


class ExportError(Exception):
    """Exception raised when export operations fail."""
    pass


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    config = {
        "required_setting": "value",
        "optional_setting": "optional_value"
    }
    
    feature = NewFeature(config)
    
    # Example data processing
    sample_data = [
        {"id": "1", "text": "sample text 1"},
        {"id": "2", "text": "sample text 2"}
    ]
    
    try:
        results = feature.process_data(sample_data)
        print(f"Processing results: {results}")
        
        # Export results
        output_file = feature.export_results(results, "results.json")
        print(f"Results exported to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")






