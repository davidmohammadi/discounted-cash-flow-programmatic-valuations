import pandas as pd
import numpy as np

def pull_company_financials(company_ticker, years, api):
    """
    Pulls company financials using Financial Modeling Prep Python API & creates datetime index
    Inputs: company ticker, years of financials to pull, api key tied to account
    Financials Pulled: Income Statement, Balance Sheet, Statement of Cash Flows, Company Market Characteristics
    Source: https://site.financialmodelingprep.com/developer/docs
    """
    import requests
    
    IS_url = requests.get(
        f"https://financialmodelingprep.com/api/v3/income-statement/{company_ticker}?&apikey={api}&limit={years}"
    )
    income_statement = IS_url.json()
    
    BS_url = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company_ticker}?&apikey={api}&limit={years}"
        )
    balance_sheet = BS_url.json()
    
    CF_url = requests.get(
        f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{company_ticker}?&apikey={api}&limit={years}"
    )
    statement_of_cash_flows = CF_url.json()
    
    SC_url = requests.get(
        f"https://financialmodelingprep.com/api/v3/enterprise-values/{company_ticker}?&apikey={api}&limit={years}"
    )
    company_stock_characteristics = SC_url.json()

    try: 
        df_IS = pd.json_normalize(income_statement)
    except:
        df_IS = pd.DataFrame.from_dict(income_statement)

    try: 
        df_BS = pd.json_normalize(balance_sheet)
    except:
        df_BS = pd.DataFrame.from_dict(balance_sheet)

    try: 
        df_CF = pd.json_normalize(statement_of_cash_flows)  
    except:
        df_CF = pd.DataFrame.from_dict(statement_of_cash_flows)

    try: 
        df_SC = pd.json_normalize(company_stock_characteristics)
    except:
        df_SC = pd.DataFrame.from_dict(company_stock_characteristics)

        

    # Income Statement
    df_IS['datetime'] = pd.to_datetime(df_IS.reset_index()['date'])
    df_IS.calendarYear = df_IS.calendarYear.astype(int)
    df_IS.set_index("calendarYear", inplace = True)

    # Balance Sheet
    df_BS['datetime'] = pd.to_datetime(df_BS.reset_index()['date'])
    df_BS.calendarYear = df_BS.calendarYear.astype(int)
    df_BS.set_index("calendarYear", inplace = True)

    # Statement of Cash Flows    
    df_CF['datetime'] = pd.to_datetime(df_CF.reset_index()['date'])
    df_CF.calendarYear = df_CF.calendarYear.astype(int)
    df_CF.set_index("calendarYear", inplace = True)

    # Enterprise Value Fields
    df_SC['calendarYear'] = df_SC['date'].str.split('-', expand = True)[0]
    df_SC['datetime'] = pd.to_datetime(df_SC.reset_index()['date'])
    df_SC.calendarYear = df_SC.calendarYear.astype(int)
    df_SC.set_index("calendarYear", inplace = True)
    
    return df_IS, df_BS, df_CF, df_SC


def calculate_free_cash_flows_method_1(
    net_income, depr_amort_current_yr, depr_amort_previous_yr,
    ppe_current_yr, ppe_previous_yr, 
    inventory_current_yr, inventory_previous_yr,
    net_receivables_current_yr, net_payables_current_yr,
    net_receivables_previous_yr, net_payables_previous_yr
):
    """
    Methodology: 
    Calculates Free Cash Flows using the following method: 
        Net Income 
        + Depreciation & Amortization 
        - Capital Expenditures (including R&D)
        - Inc. in Working Capital
        = FCF
        
    Formula Source: https://www.investopedia.com/ask/answers/033015/what-formula-calculating-free-cash-flow.asp
    Revised Formula Changes Source: https://towardsdatascience.com/discounted-cash-flow-with-python-f5103921942e
    """
    
    change_working_cap = (
        (net_receivables_current_yr - net_receivables_previous_yr)
        + (net_payables_current_yr - net_payables_previous_yr)
        + (inventory_current_yr - inventory_previous_yr)
    )
    
    cap_ex = (
        (ppe_current_yr - ppe_previous_yr) 
        + depr_amort_current_yr 
    )
    
    fcf = (
        net_income
        + (depr_amort_current_yr - depr_amort_previous_yr)
        - cap_ex
        - change_working_cap
    )

    return fcf, change_working_cap, cap_ex


def calculate_average_net_income_growth_equity_earnings_method(
    df_cashFlows_dividendsPaid, 
    df_incomeStatement_netIncome, 
    df_balanceSheet_bookValueEquity
):
    """
    Input: 
        Historical Dividends Paid - Statement of Cash Flows
        Historical Net Income - Income Statement
        Historical Total Assets & Total Liabilities - Balance Sheet
    
    Methodology:
    Annual Net Income Growth Rate = Annual Retention Ratio * Annual Return on Equity
        - Retention Ratio = 1 - (Dividends/Net Income)
        - Return on Equity = Net Income/Book Value of Equity
            - Book Value of Equity = Total Assets - Total Liabilities
    
    Formula Source: Aswatch Damodaran Session 8: Estimating Growth - https://www.youtube.com/watch?v=fRNcP9xjk-8
    """
    
    # for the top 5 rows in the statement of cash flows (recent 5 years if annual, recent 5 quarters if quarterly),
    # calculate retention ratio, return on equity and net income growth rate and append to list
    df_growthRate_roe = pd.DataFrame({
        'netIncome': df_incomeStatement_netIncome,
        'dividendsPaid': -1*df_cashFlows_dividendsPaid,
        'bookValueEquity': df_balanceSheet_bookValueEquity,
    })

    df_growthRate_roe['retention_ratio'] = 1 - df_growthRate_roe['dividendsPaid']/df_growthRate_roe['netIncome']
    df_growthRate_roe['return_on_equity'] = df_growthRate_roe['netIncome']/df_growthRate_roe['bookValueEquity']
    average_growth_rate = (df_growthRate_roe['return_on_equity'] * df_growthRate_roe['retention_ratio']).mean()
    
    print(f"Average Growth Rate of Net Income = {round(100*average_growth_rate, 2)}%")
    
    return average_growth_rate


def forecast_fcf(growth_rate_temp, df_freeCashFlow_forecasts, list_years_to_forecast_temp, df_fcf_ratios):
    """
    Forecasts Free Cash Flow (to the Firm) - FCFF with a Negative, Neutral and Positive Outlook
    Inputs: Growth Rate, DataFrame of current Free Cash Flows and List of Years to Forecast 
    Utilizes the function calculate_free_cash_flows_method_1() 
    """
    
    # prepare positive & negative outlook revenue columns (they begin with the same intial value as normal revenue)
    df_freeCashFlow_forecasts.loc[
        list_years_to_forecast_temp[0]-1, 
        ['revenue_posOutlook', 'revenue_negOutlook']
    ] = df_freeCashFlow_forecasts.loc[list_years_to_forecast_temp[0]-1, 'revenue']
    
    
    for year_forecast in list_years_to_forecast_temp:
        df_freeCashFlow_forecasts.loc[year_forecast, 'revenue'] = 12
        df_freeCashFlow_forecasts.loc[year_forecast, 'revenue'] = (
            df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue'] * (
                1+growth_rate_temp
            )
        )
        df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook'] = (
            df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_posOutlook'] * (
                1+growth_rate_temp+.05
            )
        )
        df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook'] = (
            df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_negOutlook'] * (
                1+growth_rate_temp-.05
            )
        )

        df_freeCashFlow_forecasts.loc[year_forecast, ['FCF_forecast', 'change_working_cap_forecast', 'cap_ex_forecast']] = calculate_free_cash_flows_method_1(
            net_income = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue']).loc['netIncome', 'ratio_to_revenue'],
            depr_amort_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue']).loc['depreciationAndAmortization', 'ratio_to_revenue'], 
            depr_amort_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue']).loc['depreciationAndAmortization', 'ratio_to_revenue'], 
            ppe_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue']).loc['propertyPlantEquipmentNet', 'ratio_to_revenue'],
            ppe_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue']).loc['propertyPlantEquipmentNet', 'ratio_to_revenue'], 
            inventory_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue']).loc['inventory', 'ratio_to_revenue'], 
            inventory_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue']).loc['inventory', 'ratio_to_revenue'], 
            net_receivables_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue']).loc['netReceivables', 'ratio_to_revenue'], 
            net_payables_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue']).loc['accountPayables', 'ratio_to_revenue'], 
            net_receivables_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue']).loc['netReceivables', 'ratio_to_revenue'], 
            net_payables_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue']).loc['accountPayables', 'ratio_to_revenue'] 
        )
        df_freeCashFlow_forecasts.drop(['change_working_cap_forecast', 'cap_ex_forecast'], axis = 1, inplace = True)

        #print("Positive Outlook")
        df_freeCashFlow_forecasts.loc[year_forecast, ['FCF_forecast_pos', 'change_working_cap_forecast', 'cap_ex_forecast']] = calculate_free_cash_flows_method_1(
            net_income = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook']).loc['netIncome', 'ratio_to_revenue'],
            depr_amort_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook']).loc['depreciationAndAmortization', 'ratio_to_revenue'], 
            depr_amort_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_posOutlook']).loc['depreciationAndAmortization', 'ratio_to_revenue'],
            ppe_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook']).loc['propertyPlantEquipmentNet', 'ratio_to_revenue'],
            ppe_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_posOutlook']).loc['propertyPlantEquipmentNet', 'ratio_to_revenue'], 
            inventory_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook']).loc['inventory', 'ratio_to_revenue'], 
            inventory_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_posOutlook']).loc['inventory', 'ratio_to_revenue'], 
            net_receivables_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook']).loc['netReceivables', 'ratio_to_revenue'], 
            net_payables_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_posOutlook']).loc['accountPayables', 'ratio_to_revenue'], 
            net_receivables_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_posOutlook']).loc['netReceivables', 'ratio_to_revenue'], 
            net_payables_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_posOutlook']).loc['accountPayables', 'ratio_to_revenue'] 
        )
        df_freeCashFlow_forecasts.drop(['change_working_cap_forecast', 'cap_ex_forecast'], axis = 1, inplace = True)

        #print("Negative Outlook")
        df_freeCashFlow_forecasts.loc[year_forecast, ['FCF_forecast_neg', 'change_working_cap_forecast', 'cap_ex_forecast']] = calculate_free_cash_flows_method_1(
            net_income = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook']).loc['netIncome', 'ratio_to_revenue'],
            depr_amort_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook']).loc['depreciationAndAmortization', 'ratio_to_revenue'], 
            depr_amort_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_negOutlook']).loc['depreciationAndAmortization', 'ratio_to_revenue'],
            ppe_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook']).loc['propertyPlantEquipmentNet', 'ratio_to_revenue'],
            ppe_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_negOutlook']).loc['propertyPlantEquipmentNet', 'ratio_to_revenue'], 
            inventory_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook']).loc['inventory', 'ratio_to_revenue'], 
            inventory_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_negOutlook']).loc['inventory', 'ratio_to_revenue'], 
            net_receivables_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook']).loc['netReceivables', 'ratio_to_revenue'], 
            net_payables_current_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast, 'revenue_negOutlook']).loc['accountPayables', 'ratio_to_revenue'], 
            net_receivables_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_negOutlook']).loc['netReceivables', 'ratio_to_revenue'], 
            net_payables_previous_yr = (df_fcf_ratios*df_freeCashFlow_forecasts.loc[year_forecast-1, 'revenue_negOutlook']).loc['accountPayables', 'ratio_to_revenue'] 
        )
        df_freeCashFlow_forecasts.drop(['change_working_cap_forecast', 'cap_ex_forecast'], axis = 1, inplace = True)
        
    return df_freeCashFlow_forecasts


def calculate_ratio_of_FCF_components_to_revenue(df_fcf, ratio_year_set):
    """
    Takes dataframe of FCF components and calculates the ratio of components to Revenue
    ratio_year_set defines what year to set the ratio from, 'all' uses the average ratio from all years of data
    """
    
    
    df_fcf_ratios = pd.DataFrame(columns = ['ratio_to_revenue'])
    if ratio_year_set == "all":
        df_fcf_ratios.loc['netIncome'] = (
            df_fcf.loc[:, 'netIncome'].mean()/df_fcf.loc[:, 'revenue'].mean()
        )
        df_fcf_ratios.loc['depreciationAndAmortization'] = (
            df_fcf.loc[:, 'depreciationAndAmortization'].mean()/df_fcf.loc[:, 'revenue'].mean()
        )
        df_fcf_ratios.loc['inventory'] = (
            df_fcf.loc[:, 'inventory'].mean()/df_fcf.loc[:, 'revenue'].mean()
        )
        df_fcf_ratios.loc['propertyPlantEquipmentNet'] = (
            df_fcf.loc[:, 'propertyPlantEquipmentNet'].mean()/df_fcf.loc[:, 'revenue'].mean()
        )
        df_fcf_ratios.loc['netReceivables'] = (
            df_fcf.loc[:, 'netReceivables'].mean()/df_fcf.loc[:, 'revenue'].mean()
        )
        df_fcf_ratios.loc['accountPayables'] = (
            df_fcf.loc[:, 'accountPayables'].mean()/df_fcf.loc[:, 'revenue'].mean()
        )
        
    else: 
        df_fcf_ratios.loc['netIncome'] = (
            df_fcf.loc[ratio_year_set, 'netIncome']/df_fcf.loc[ratio_year_set, 'revenue']
        )
        df_fcf_ratios.loc['depreciationAndAmortization'] = (
            df_fcf.loc[ratio_year_set, 'depreciationAndAmortization']/df_fcf.loc[ratio_year_set, 'revenue']
        )
        df_fcf_ratios.loc['inventory'] = (
            df_fcf.loc[ratio_year_set, 'inventory']/df_fcf.loc[ratio_year_set, 'revenue']
        )
        df_fcf_ratios.loc['propertyPlantEquipmentNet'] = (
            df_fcf.loc[ratio_year_set, 'propertyPlantEquipmentNet']/df_fcf.loc[ratio_year_set, 'revenue']
        )
        df_fcf_ratios.loc['netReceivables'] = (
            df_fcf.loc[ratio_year_set, 'netReceivables']/df_fcf.loc[ratio_year_set, 'revenue']
        )
        df_fcf_ratios.loc['accountPayables'] = (
            df_fcf.loc[ratio_year_set, 'accountPayables']/df_fcf.loc[ratio_year_set, 'revenue']
        )
    
    return df_fcf_ratios


def calculate_interest_coverage_ratio_and_synthetic_rating(ebitda, deprAndAmort, interestExpense, risk_free_rate):
    """
    Calculates a synthetic rating for a company using interest coverage ratio as a proxy
    Inputs: EBITA, Depreciation & Amortization, Interest Expense & Risk Free Rate

    Methodology Source: Aswath Damodaran https://youtu.be/N_FH89DCdGs
    """
    
    interest_coverage_ratio = (
        ebitda - deprAndAmort
    )/interestExpense
    
    bins = [-np.inf, 0.5, 0.8, 1.25, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 6, 7.5, 9.5, 12.5, np.inf]
    rating = ['D', 'C', 'CC', 'CCC', 'B-', 'B', 'B+', 'BB', 'BB+', 'BBB', 'A-', 'A', 'A+', 'AA', 'AAA']
    dict_rating_spread = {
        'D': 0.1434,
        'C': 0.1076,
        'CC': 0.088,
        'CCC': 0.0778,
        'B-': 0.0462,
        'B': 0.0378,
        'B+': 0.0315,
        'BB': 0.0215,
        'BB+': 0.0193,
        'BBB': 0.0159,
        'A-': 0.0129,
        'A': 0.014,
        'A+': 0.0103,
        'AA': 0.0082,
        'AAA': 0.0067
    }

    credit_default_spread = pd.cut(
        pd.DataFrame(data = [interest_coverage_ratio])[0], bins, labels=rating
    ).map(dict_rating_spread)[0]
    cost_of_debt = credit_default_spread + risk_free_rate

    print(
    f"""
    Interest Coverage Ratio = {round(interest_coverage_ratio, 2)}
    Synthetic Rating = {pd.cut(
        pd.DataFrame(data = [interest_coverage_ratio])[0], bins, labels=rating)[0]}
    Credit Default Spread = {round(100*credit_default_spread, 2)}%
    Risk Free Rate = {round(100*risk_free_rate, 2)}%
    Cost of Debt = {round(100*cost_of_debt, 2)}%"""
    )
    
    return interest_coverage_ratio, cost_of_debt


def pull_daily_stock_prices(list_of_tickers, market_data_startDate, market_data_endDate):
    """
    Function pulls daily prices of given stocks using Pandas DataReader off Yahoo
    Calculates Daily & Monthly return for the given stocks and returns 3 dataframes: 
    Daily Prices, Daily Returns, Monthly Returns
    """
    import pandas_datareader as web
    
    df_dailyStockPrices = web.DataReader(
        list_of_tickers,
        'yahoo',
        market_data_startDate,
        market_data_endDate
    )['Close']
    
    df_dailyReturn = df_dailyStockPrices.pct_change()
    df_monthlyReturn = df_dailyStockPrices.groupby(pd.Grouper(freq='M')).head(1).pct_change().iloc[1:]
    df_dailyReturn.dropna(inplace = True)

    return df_dailyStockPrices, df_dailyReturn, df_monthlyReturn


def calculate_company_expected_return_CAPM(df_company_returns, df_index_returns, risk_free_rate, company_ticker):
    """
    Takes company & index daily returns and calculates the beta, market return and then expected stock return with CAPM
    Uses scipy package to run the linear regression against market & stock returns 
    """
    
    from scipy import stats
    # https://gist.github.com/PyDataBlog/3f03b4369a795b41ddfd49536bb5adc8
    X = df_index_returns
    y = df_company_returns

    beta, intercept, r_value, p_value, std_err = stats.linregress(X, y)
    
    # Average Daily Market Return
    market_return = df_index_returns.mean() * 252
    print(f"Market Return = {round(100*market_return, 2)}%")
    
    # CAPM: E[R] Expected Return
    expected_stock_return = risk_free_rate + beta * (market_return - risk_free_rate)
    print(f"Expected Return ({company_ticker}) = {round(100*expected_stock_return, 2)}%")
    
    return expected_stock_return, market_return


def calculate_WACC(total_equity, total_debt, eff_tax_rate, stock_return, cost_of_debt):
    
    wacc = (
        cost_of_debt * (1 - eff_tax_rate) * (total_debt/(total_debt + total_equity))
        + stock_return * (total_equity/(total_debt + total_equity)) 
    )
    print(f"Weighted Average Cost of Capital (WACC) = {round(100*wacc, 2)}%")
    return wacc


def calculate_terminal_enterprise_equity_values(
    df_FCF_selectedGrowthMethod, wacc, cashAndCashEquivalents, totalDebt, numShares, growth_rate_perpetuity = 0.02
):
    """
    Function calculates the Enterprise, Terminal and Equity Values of the given stock
    Inputs: WACC, Forecasted FCF, perpetual growth rate (default = 2% ~ inflation)
    - Terminal Value = [Forecasted FCF * (1+g)]/(WACC - g)
    - Enterprise Value = PV(all Forecasted Free Cash Flows + Terminal Value)
    - Equity Value = (Enterprise Value + Cash - Debt)/#-shares-outstanding
    
    Function created by David Mohammadi
    """

    import numpy_financial as npf
    
    # Create dataframe to store valuations
    df_equity_valuations = pd.DataFrame(index = ['neutral_outlook', 'positive_outlook', 'negative_outlook'])
    
    # Discounted Forecasted Free Cash Flows
    list_FCF_forecasts_stable = df_FCF_selectedGrowthMethod.loc[2022:, 'FCF_forecast'].to_list()
    list_FCF_forecasts_positive = df_FCF_selectedGrowthMethod.loc[2022:, 'FCF_forecast_pos'].to_list()
    list_FCF_forecasts_negative = df_FCF_selectedGrowthMethod.loc[2022:, 'FCF_forecast_neg'].to_list()

    df_equity_valuations.loc[['neutral_outlook', 'positive_outlook', 'negative_outlook'], 'npv_FCFF'] = [
        npf.npv(wacc, list_FCF_forecasts_stable),
        npf.npv(wacc, list_FCF_forecasts_positive),
        npf.npv(wacc, list_FCF_forecasts_negative)
    ]
    # terminal value
    df_terminal_values_outlooks = pd.DataFrame((
        df_FCF_selectedGrowthMethod.rename(columns = {
                'FCF_forecast': "neutral_outlook",
                'FCF_forecast_pos': "positive_outlook",
                'FCF_forecast_neg': "negative_outlook"
        }).iloc[-1, :][['neutral_outlook', 'positive_outlook', 'negative_outlook']]
            * (1+growth_rate_perpetuity)
    )/(wacc - growth_rate_perpetuity)).rename(columns = {2026: "terminal_value"})

    df_equity_valuations['terminal_value_discounted'] = (
        df_terminal_values_outlooks['terminal_value']
        /(1+wacc)**5
    )
    
    # enterprise value
    df_equity_valuations['enterprise_value'] = (
        df_equity_valuations['npv_FCFF'] + df_equity_valuations['terminal_value_discounted']
    )
    
    # equity value
    df_equity_valuations['estimate_stock_price'] = ((
        df_equity_valuations['enterprise_value'] 
        + cashAndCashEquivalents
        - totalDebt
    )/numShares)[['positive_outlook', 'neutral_outlook', 'negative_outlook']]
    
    return df_terminal_values_outlooks, df_equity_valuations