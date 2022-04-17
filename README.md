# DCF Programmatic Valuations
Personal functions &amp; code written as I learned the process of a discounted cash flow valuation. Pulls financials from FinancialModelingPrep and ends with valued stock price(s) 

## DCF Model - Process
Steps: 
1. Historical Free Cash Flow Calculation
1. Free Cash Flow Forecasting
    1. Estimating Growth
        - Growth via Equity Earnings & Return on Equity
        - Historical Growth
    1. Ratio: FCF Financial Components to Revenue
    1. Forecast Net Revenues & Calculate Future FCF
1. Weighted Average Cost of Capital (WACC) Calculation
    1. Cost of Debt
        - Interest Coverage Ratio & Synthetic Rating
    2. Cost of Equity
        - CAPM 
            - Pull stock price & index data
    3. Effective Tax Rate
1. Terminal, Enterprise & Equity Valuations

## Created DCF functions
<b>pull_company_financials()</b>
- Pulls given (ticker) company financials using Financial Modeling Prep Python API
- Financials pulled: Income Statement, Balance Sheet, Statement of Cash Flows, Company Market Characteristics

<b>calculate_free_cash_flows_method_1()</b>
- Calculates current year Free Cash Flows (to the firm) using financial statement line-items 
    - Formula source: Investopedia
    - Formula revisions: Jose Manu (Towards Data Science Article)

<b>calculate_average_net_income_growth_equity_earnings_method()</b>
- Calculates the net income growth of a company by looking at the return on equity & retention ratio
    - Formula source: Aswath Damodaran Valuation Lectures

<b>forecast_fcf()</b>
- Forecasts free cash flow (to the firm) for given future years, provides a positive, neutral & negative outlook using (+/-) 5% interval to given growth rate

<b>calculate_ratio_of_FCF_components_to_revenue()</b>
- Calculates the ratio of free cash flow components to firm's revenue, user can specify which year of revenue/components to use (or average of all years)

<b>calculate_interest_coverage_ratio_and_synthetic_rating()</b>
- Calculates a synthetic rating for a company using interest coverage ratio as a proxy
    - Inputs: EBITA, Depreciation & Amortization, Interest Expense & Risk Free Rate
    - Formula source: Aswath Damodaran Valuation Lectures

<b>pull_daily_stock_prices()</b>
- Pulls daily prices of given stock tickers using Pandas DataReader off Yahoo Finance then calculates daily & monthly return for the given stocks 

<b>calculate_company_expected_return_CAPM()</b>
- Takes company & index daily returns and calculates the beta, market return and then expected stock return with CAPM, used to calculate cost of equity

<b>calculate_WACC()</b>
- Calculates the weighted average cost of capital (WACC) 
    - Formula source: Aswath Damodaran Valuation Lectures

<b>calculate_terminal_enterprise_equity_values()</b>
- calculates the Enterprise, Terminal and Equity Values of the given stock
    - Terminal Value = [Forecasted FCF * (1+g)]/(WACC - g)
    - Enterprise Value = PV(all Forecasted Free Cash Flows + Terminal Value)
    - Equity Value = (Enterprise Value + Cash - Debt)/#-shares-outstanding


## Sources of Logic & Learnings
- [Aswath Damodaran Valuation Lectures](https://youtube.com/playlist?list=PLUkh9m2BorqnKWu0g5ZUps_CbQ-JGtbI9)
- [Investopedia](https://www.investopedia.com/ask/answers/033015/what-formula-calculating-free-cash-flow.asp)
- [Jose Manu - Towards Data Science](https://towardsdatascience.com/discounted-cash-flow-with-python-f5103921942e)
