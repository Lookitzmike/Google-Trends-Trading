import pandas as pd             # Data analysis
import numpy as np              # Transform data
from datetime import timedelta

class GoogleTrendTrading(QCAlgorithm):

    def Initialize(self):
        # InteractiveBrokers: Supported Order Type = Market Order, Limit Order, Stop Market, Stop Limit Order, Market On Open, Market on Close
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage)       # Documentation: /algorithm-reference/reality-modelling
        self.SetStartDate(2004, 1, 1)                                           # Set Start Date
        self.SetEndDate(2018, 9, 30)                                            # Set End Date
        self.SetCash(100000)                                                    # Set Cash to $100,000
        self.equity = ['AAPL', 'AMZN']
        self.months = {}                                                        # Empty months array
        self.AddEquity(self.equity[0], Resolution.Hour)                         # Aquire hourly data
        self.AddEquity(self.equity[1], Resolution.Hour)

        # https://www.quantconnect.com/docs/algorithm-reference/importing-custom-data
        file = self.Download("https://www.dropbox.com/s/s22hx31zgjshngr/stockTrendData.csv?dl=1")
        # Currently the data is in the file is read as '2004-01,69\r', '2004-02,60\r', '2004-03,54\r', '2004-04,55\r' ; \r = next row
        # Need to split the date from the number so we need to remove the comma and store the dates into Google_Trends Columns Months and Interest

        # Prepare dataset
        self.rowCount = sum(1 for row in file)                    # Count the number of rows in csv file for debugging
        self.Google_Trends = pd.DataFrame([x.split(',') for x in file.split('\r\n')[1:]],
            columns=['Week', 'interest'])
        # Creating DataFrame Columns Months | interest, splits the rows removing the commas, split file to remove \r\n, moving data from csv file to DataFrame

        # Calculate the Moving Average of the last 3 and 18 month data volume
        # MA3 = (n(t-1) + n(t-2) + n(t-3))/3, where n(t-1) is the volume of the last available month
        self.Google_Trends["MA3"] = self.Google_Trends.interest.rolling(3).mean()
        self.Google_Trends["MA18"] = self.Google_Trends.interest.rolling(18).mean()
        # Equation from: https://seekingalpha.com/article/4202781-timing-market-google-trends-search-volume-data
        ''' Strategy from above website:
            For falling search volume, MA3 < MA18, we buy equity[0] at the closing price, on the first trading day of the first week of month,
        and subsequently sell the fund at the closing price on the first trading day of the first week of the next month.
            For rising search volume, MA3 > MA18, we buy equity[1] at the closing price on the first trading day of the first week of month,
        and sell the funds at the closing price on the first trading day of the first week of the next month.
            If conditions MA3 < MA18 or MA3 > MA18 exists for several successive months, then above method ensures that equity are held for
        several months, since the method would sell and buy the same ETF simultaneously if conditions do not change.
        '''

        self.Google_Trends["Signal"] = self.Google_Trends["MA3"].astype('float') - self.Google_Trends["MA18"].astype('float')
        self.Google_Trends["Signal"] = self.Google_Trends["Signal"].shift(1)

    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.

        Arguments:
            data: Slice object keyed by symbol containing the stock data
        '''
        date_today = self.Time.date()                                           # Starting Date: 2010-01, 2010-02, ...
        date_today = date_today.strftime(format = '%Y-%m-%d')                   # Convert string to time
        date_today = date_today[0:7]                                            # Limit dates to months [0:7] = [0123-56] = [2010-01]

        # https://www.quantconnect.com/research/cache/0b0052c163465e826d6ac11b70d6aee2.html
        signal = self.Google_Trends.loc[self.Google_Trends.Week == date_today,"Signal"].iloc[0]
        # .LOC gets row/column from with labels from index; .ILOC gets row/column from position in index

        try:
            invested = self.months[date_today]
        except:
            invested = "No"
        if self.Time.hour == 15 and invested == "No":

            if self.Portfolio[self.equity[0]].Quantity > 0 and signal > 0:  #
                self.Liquidate(self.equity[0])                              #
            if self.Portfolio[self.equity[1]].Quantity > 0 and signal < 0:  #
                self.Liquidate(self.equity[1])                              #
                                                                            #
            if signal < 0 and self.Portfolio[self.equity[0]].Quantity == 0: #
                self.SetHoldings(self.equity[0], 1)                         #
                self.months[date_today] = "Yes"                             #
                return                                                      #
            if signal > 0 and self.Portfolio[self.equity[1]].Quantity == 0: #
                self.SetHoldings(self.equity[1], 1)                         #
                self.months[date_today] = "Yes"                             #
                return                                                      #

        # ___Debug___
        #self.Debug(todaysDate)                 # Print dates
        self.Debug(self.Google_Trends)          # Dataset info
