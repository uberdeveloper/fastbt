=========
History
=========
v0.8.0
------
* **NEW**: Added statistical testing skill v1.0-alpha with comprehensive test scripts
  * Includes hypothesis testing for trading strategy validation
  * Supports benchmark comparison, conditional analysis, and temporal validation
  * Added out-of-sample testing capabilities
* **ENHANCED**: Simulation module improvements
  * Refactored generators into Time and Sequence engines
  * Added IID lognormal distribution support
  * New generator modes and parameters for more flexible simulation
  * Fixed price stagnation in tick/quote generators
* Added regression tests for tick generator price movement
* Updated documentation for simulation module with new examples
* Code quality improvements with pre-commit hooks

v0.7.0 (BREAKING)
------
* **BREAKING**: Migrated to Pydantic v2.0 compatibility (requires pydantic>=2.0.0)
* Updated all BaseModel classes to use model_config instead of deprecated Config class
* Replaced root_validator with model_validator(mode='before')
* Added default values for Optional fields as required by Pydantic v2
* Enhanced option chain simulation capabilities
* Added correlated data simulation features
* Improved URL pattern matching functionality
* Code formatting and linting improvements with ruff and black
* Added `load-data` skill for efficient data discovery and loading (includes peek_file, efficient_load, collate_data, and normalize_json)

v0.6.0
------
* New methods added to `TradeBook` object
 * mtm - to calculate mtm for open positions
 * clear - to clear the existing entries
 * helper attributes for positions
* `order_fill_price` method added to utils to simulate order quantity

v0.5.1
------
* Simple bug fixes added

v0.5.0
------
* `OptionExpiry` class added to calculate option payoffs based on expiry

v0.4.0
-------
* Brokers module deprecation warning added
* Options module revamped

v0.3.0 (2019-03-15)
--------------------
* More helper functions added to utils
* Tradebook class enhanced
* A Meta class added for event based simulation

v0.2.0 (2018-12-26)
--------------------
* Backtest from different formats added
* Rolling function added


v0.1.0. (2018-10-13)
----------------------

* First release on PyPI
