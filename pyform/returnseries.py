import logging

log = logging.getLogger(__name__)

import copy
import math
import pandas as pd
from typing import Callable, Optional, Union
from pyform.timeseries import TimeSeries


class ReturnSeries(TimeSeries):
    """A return series. It should be datetime indexed and
       has one column of returns data.
    """

    def __init__(self, df):

        super().__init__(df)

        self.benchmark = dict()
        self.risk_free = dict()

    @classmethod
    def read_fred_libor_1m(cls):
        """Create one month libor daily returns from fred data

        Returns:
            pyform.ReturnSeries: one month libor daily returns
        """

        # Load St.Louis Fed Data
        libor1m = pd.read_csv(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=USD1MTD156N"
        )

        # Format Data
        libor1m.columns = ["date", "LIBOR_1M"]
        libor1m = libor1m[libor1m["LIBOR_1M"] != "."]
        libor1m["LIBOR_1M"] = libor1m["LIBOR_1M"].astype(float)
        libor1m["LIBOR_1M"] = libor1m["LIBOR_1M"] / 100

        # Create Return Series
        libor1m = cls(libor1m)

        # Daily Value is in Annualized Form, Change it to Daily Return
        one_year = pd.to_timedelta(365.25, unit="D")
        years = (libor1m.end - libor1m.start) / one_year
        sample_per_year = len(libor1m.series.index) / years
        libor1m._series["LIBOR_1M"] += 1
        libor1m._series["LIBOR_1M"] **= 1 / sample_per_year
        libor1m._series["LIBOR_1M"] -= 1
        libor1m.series = libor1m._series.copy()

        return libor1m

    @staticmethod
    def _compound_geometric(returns: pd.Series) -> float:
        """Performs geometric compounding.

        e.g. if there are 3 returns r1, r2, r3,
        calculate (1+r1) * (1+r2) * (1+r3) - 1

        Args:
            returns: pandas series of returns, in decimals.
                i.e. 3% should be expressed as 0.03, not 3.

        Returns:
            float: total compounded return
        """

        return (1 + returns).prod() - 1

    @staticmethod
    def _compound_arithmetic(returns: pd.Series) -> float:
        """Performs arithmatic compounding.

        e.g. if there are 3 returns r1, r2, r3,
        calculate ``r1 + r2`` + r3

        Args:
            returns: pandas series of returns, in decimals.
                i.e. 3% should be expressed as 0.03, not 3.

        Returns:
            float: total compounded return
        """

        return sum(returns)

    @staticmethod
    def _compound_continuous(returns: pd.Series) -> float:
        """Performs continuous compounding.

        e.g. if there are 3 returns r1, r2, r3,
        calculate exp(``r1 + r2`` + r3) - 1

        Args:
            returns: pandas series of returns, in decimals.
                i.e. 3% should be expressed as 0.03, not 3.

        Returns:
            float: total compounded return
        """

        return math.exp(sum(returns)) - 1

    def _compound(self, method: str) -> Callable:

        compound = {
            "arithmetic": self._compound_arithmetic,
            "geometric": self._compound_geometric,
            "continuous": self._compound_continuous,
        }

        return compound[method]

    def to_period(self, freq: str, method: str) -> pd.DataFrame:
        """Converts return series to a different (and lower) frequency.

        Args:
            freq: frequency to convert the return series to.
                Available options can be found `here <https://tinyurl.com/t78g6bh>`_.
            method: compounding method when converting to lower frequency.

                * 'geometric': geometric compounding ``(1+r1) * (1+r2) - 1``
                * 'arithmetic': arithmetic compounding ``r1 + r2``
                * 'continuous': continous compounding ``exp(r1+r2) - 1``

        Returns:
            pd.DataFrame: return series in desired frequency
        """

        if freq == "D":
            # Use businessness days for all return series
            freq = "B"

        try:
            assert self._freq_compare(freq, self.freq)
        except AssertionError:
            raise ValueError(
                "Cannot convert to higher frequency. "
                f"target={freq}, current={self.freq}"
            )

        if method not in ["arithmetic", "geometric", "continuous"]:
            raise ValueError(
                "Method should be one of 'geometric', 'arithmetic' or 'continuous'"
            )

        return self.series.groupby(pd.Grouper(freq=freq)).agg(self._compound(method))

    def to_week(self, method: Optional[str] = "geometric") -> pd.DataFrame:
        """Converts return series to weekly frequency.

        Args:
            method: compounding method. Defaults to "geometric".

                * 'geometric': geometric compounding ``(1+r1) * (1+r2) - 1``
                * 'arithmetic': arithmetic compounding ``r1 + r2``
                * 'continuous': continous compounding ``exp(r1+r2) - 1``

        Returns:
            pd.DataFrame: return series, in weekly frequency
        """

        return self.to_period("W", method)

    def to_month(self, method: Optional[str] = "geometric") -> pd.DataFrame:
        """Converts return series to monthly frequency.

        Args:
            method: compounding method. Defaults to "geometric".

                * 'geometric': geometric compounding ``(1+r1) * (1+r2) - 1``
                * 'arithmetic': arithmetic compounding ``r1 + r2``
                * 'continuous': continous compounding ``exp(r1+r2) - 1``

        Returns:
            pd.DataFrame: return series, in monthly frequency
        """

        return self.to_period("M", method)

    def to_quarter(self, method: Optional[str] = "geometric") -> pd.DataFrame:
        """Converts return series to quarterly frequency.

        Args:
            method: compounding method. Defaults to "geometric".

                * 'geometric': geometric compounding ``(1+r1) * (1+r2) - 1``
                * 'arithmetic': arithmetic compounding ``r1 + r2``
                * 'continuous': continous compounding ``exp(r1+r2) - 1``

        Returns:
            pd.DataFrame: return series, in quarterly frequency
        """

        return self.to_period("Q", method)

    def to_year(self, method: Optional[str] = "geometric") -> pd.DataFrame:
        """Converts return series to annual frequency.

        Args:
            method: compounding method. Defaults to "geometric".

                * 'geometric': geometric compounding ``(1+r1) * (1+r2) - 1``
                * 'arithmetic': arithmetic compounding ``r1 + r2``
                * 'continuous': continous compounding ``exp(r1+r2) - 1``

        Returns:
            pd.DataFrame: return series, in annual frequency
        """

        return self.to_period("Y", method)

    def _normalize_daterange(self, series: "ReturnSeries"):

        series = copy.deepcopy(series)
        series.set_daterange(start=self.start, end=self.end)

        return series

    def add_benchmark(self, benchmark: "ReturnSeries", name: Optional[str] = None):
        """Add a benchmark for the return series. A benchmark is useful and needed
           in order to calculate:

                * 'correlation': is the correlation between the return series and
                    the benchmark
                * 'beta': is the CAPM beta between the return series and the benchmark

        Args:
            benchmark: A benchmark. Should be a ReturnSeries object.
            name: name of the benchmark. This will be used to display results. Defaults
                to "None", which will use the column name of the benchmark.
        """

        if name is None:
            name = benchmark.series.columns[0]

        log.info(f"Adding benchmark. name={name}")
        self.benchmark[name] = benchmark

    def get_corr(
        self,
        freq: Optional[str] = "M",
        method: Optional[str] = "pearson",
        compound_method: Optional[str] = "geometric",
        meta: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Calculates correlation of the return series with its benchmarks

        Args:
            freq: Returns are converted to the same frequency before correlation
                is compuated. Defaults to "M".
            method: {'pearson', 'kendall', 'spearman'}. Defaults to "pearson".

                * pearson : standard correlation coefficient
                * kendall : Kendall Tau correlation coefficient
                * spearman : Spearman rank correlation

            compound_method: {'geometric', 'arithmetic', 'continuous'}.
                Defaults to "geometric".

            meta: whether to include meta data in output. Defaults to False.
                Available meta are:

                * freq: frequency used to compute correlation
                * method: method used to compute correlation
                * start: start date for calculating correlation
                * end: end date for calculating correlation
                * total: total number of data points in returns series
                * skipped: number of data points skipped when computing correlation

        Raises:
            ValueError: when no benchmark is set

        Returns:
            pd.DataFrame: correlation results with the following columns

                * benchmark: name of the benchmark
                * field: name of the field. In this case, it is 'correlation' for all
                * value: correlation value

            Data described in meta will also be available in the returned DataFrame if
            meta is set to True.
        """

        if not len(self.benchmark) > 0:
            raise ValueError("Correlation needs at least one benchmark.")

        ret = self.to_period(freq=freq, method=compound_method)
        n_ret = len(ret.index)

        # Columns in the returned dataframe
        bm_names = []
        corr = []
        start = []
        end = []
        skipped = []

        for name, benchmark in self.benchmark.items():

            try:

                # Modify benchmark so it's in the same timerange as the returns series
                benchmark = self._normalize_daterange(benchmark)

                # Convert benchmark to desired frequency
                # note this is done after it's time range has been normalized
                # this is important as otherwise when frequency is changed, we may
                # include additional days in the calculation
                bm_ret = benchmark.to_period(freq=freq, method=compound_method)

                # Join returns and benchmark to calculate correlation
                df = ret.join(bm_ret, on="datetime", how="inner")

                # Add correlation to list
                corr.append(df.corr(method).iloc[0, 1])

                # Add benchmark to list of benchmark names
                bm_names.append(name)

                if meta:
                    # Add start and end date used to compute correlation
                    start.append(benchmark.start)
                    end.append(benchmark.end)

                    # Add number of rows skipped in calculation
                    skipped.append(n_ret - len(df.index))

            except Exception as e:  # pragma: no cover

                log.error(f"Cannot compute correlation: benchmark={name}: {e}")
                pass

        if meta:

            result = pd.DataFrame(
                data={
                    "name": bm_names,
                    "field": "correlation",
                    "value": corr,
                    "freq": freq,
                    "method": method,
                    "start": start,
                    "end": end,
                    "total": n_ret,
                    "skipped": skipped,
                }
            )

        else:

            result = pd.DataFrame(
                data={"name": bm_names, "field": "correlation", "value": corr}
            )

        return result

    def get_total_return(
        self,
        include_bm: Optional[bool] = True,
        method: Optional[str] = "geometric",
        meta: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Compute total return of the series

        Args:
            include_bm: whether to compute total return for benchmarks as well.
                Defaults to True.
            method: method to use when compounding total return.
                Defaults to "geometric".
            meta: whether to include meta data in output. Defaults to False.
                Available meta are:

                * method: method used to compound total return
                * start: start date for calculating total return
                * end: end date for calculating total return

        Returns:
            pd.DataFrame: total return results with the following columns

                * name: name of the series
                * field: name of the field. In this case, it is 'total return' for all
                * value: total return value, in decimals

            Data described in meta will also be available in the returned DataFrame if
            meta is set to True.
        """

        # Columns in the returned dataframe
        names = []
        total_return = []
        start = []
        end = []

        names.append(self.series.columns[0])
        total_return.append(self._compound(method)(self.series.iloc[:, 0]))
        start.append(self.start)
        end.append(self.end)

        if include_bm:
            for name, benchmark in self.benchmark.items():

                try:

                    # Modify benchmark so it's in the same timerange as the
                    # returns series
                    benchmark = self._normalize_daterange(benchmark)
                    names.append(name)
                    total_return.append(
                        self._compound(method)(benchmark.series.iloc[:, 0])
                    )

                    if meta:
                        start.append(benchmark.start)
                        end.append(benchmark.end)

                except Exception as e:  # pragma: no cover

                    log.error(f"Cannot compute total return: benchmark={name}: {e}")
                    pass

        if meta:

            result = pd.DataFrame(
                data={
                    "name": names,
                    "field": "total return",
                    "value": total_return,
                    "method": method,
                    "start": start,
                    "end": end,
                }
            )

        else:

            result = pd.DataFrame(
                data={"name": names, "field": "total return", "value": total_return}
            )

        return result

    def get_annualized_return(
        self,
        method: Optional[str] = "geometric",
        include_bm: Optional[bool] = True,
        meta: Optional[bool] = False,
    ):
        """Compute annualized return of the series

        Args:
            method: method to use when compounding return. Defaults to "geometric".
            include_bm: whether to compute annualized return for benchmarks as well.
                Defaults to True.
            meta: whether to include meta data in output. Defaults to False.
                Available meta are:

                * method: method used to compound annualized return
                * start: start date for calculating annualized return
                * end: end date for calculating annualized return

        Returns:
            pd.DataFrame: annualized return results with the following columns

                * name: name of the series
                * field: name of the field. In this case, it is 'annualized return'
                    for all
                * value: annualized return value, in decimals

            Data described in meta will also be available in the returned DataFrame if
            meta is set to True.
        """

        result = self.get_total_return(method=method, include_bm=include_bm, meta=True)
        result["field"] = "annualized return"

        # find number of days
        one_day = pd.to_timedelta(1, unit="D")
        result["days"] = (result["end"] - result["start"]) / one_day

        years = result["days"] / 365.25
        if method == "geometric":
            result["value"] = (1 + result["value"]) ** (1 / years) - 1
        elif method == "arithmetic":
            result["value"] = result["value"] * (1 / years)
        elif method == "continuous":
            result["value"] = (result["value"] + 1).apply(math.log) * (1 / years)

        if meta:
            result = result[["name", "field", "value", "method", "start", "end"]]
        else:
            result = result[["name", "field", "value"]]

        return result

    def get_annualized_volatility(
        self,
        freq: Optional[str] = "M",
        include_bm: Optional[bool] = True,
        method: Optional[str] = "sample",
        compound_method: Optional[str] = "geometric",
        meta: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Compute annualized volatility of the series

        Args:
            freq: Returns are converted to the same frequency before volatility
                is compuated. Defaults to "M".
            include_bm: whether to compute annualized volatility for benchmarks as well.
                Defaults to True.
            method: {'sample', 'population'}. method used to compute volatility
                (standard deviation). Defaults to "sample".
            compound_method: method to use when compounding return.
                Defaults to "geometric".
            meta: whether to include meta data in output. Defaults to False.
                Available meta are:

                * freq: frequency of the series
                * method: method used to compute annualized volatility
                * start: start date for calculating annualized volatility
                * end: end date for calculating annualized volatility

        Returns:
            pd.DataFrame: annualized volatility results with the following columns

                * name: name of the series
                * field: name of the field. In this case, it is 'annualized volatility'
                    for all
                * value: annualized volatility value, in decimals

            Data described in meta will also be available in the returned DataFrame if
            meta is set to True.
        """

        # delta degrees of freedom, used for calculate standard deviation
        ddof = {"sample": 1, "population": 0}[method]

        # Columns in the returned dataframe
        names = []
        ann_vol = []
        start = []
        end = []

        # Convert series to the desired frequency
        ret = self.to_period(freq=freq, method=compound_method)

        # To annualize, after changing the frequency, see how many
        # periods there are in a year
        one_year = pd.to_timedelta(365.25, unit="D")
        years = (self.end - self.start) / one_year
        sample_per_year = len(ret.index) / years

        vol = ret.iloc[:, 0].std(ddof=ddof)
        vol *= math.sqrt(sample_per_year)

        names.append(ret.columns[0])
        ann_vol.append(vol)
        start.append(self.start)
        end.append(self.end)

        if include_bm:
            for name, benchmark in self.benchmark.items():

                try:

                    # Modify benchmark so it's in the same timerange as the
                    # returns series
                    benchmark = self._normalize_daterange(benchmark)
                    bm = benchmark.to_period(freq=freq, method=compound_method)

                    years = (benchmark.end - benchmark.start) / one_year
                    sample_per_year = len(bm.index) / years

                    vol = bm.iloc[:, 0].std(ddof=ddof)
                    vol *= math.sqrt(sample_per_year)

                    names.append(name)
                    ann_vol.append(vol)

                    if meta:
                        start.append(benchmark.start)
                        end.append(benchmark.end)

                except Exception as e:  # pragma: no cover

                    log.error(
                        "Cannot compute annualized volatility: "
                        f"benchmark={name}: {e}"
                    )
                    pass

        if meta:

            result = pd.DataFrame(
                data={
                    "name": names,
                    "field": "annualized volatility",
                    "value": ann_vol,
                    "freq": freq,
                    "method": method,
                    "start": start,
                    "end": end,
                }
            )

        else:

            result = pd.DataFrame(
                data={"name": names, "field": "annualized volatility", "value": ann_vol}
            )

        return result

    def get_sharpe_ratio(
        self,
        freq: Optional[str] = "M",
        risk_free: Optional[Union[float, int, str]] = 0,
        include_bm: Optional[bool] = True,
        compound_method: Optional[str] = "geometric",
        meta: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Compute Sharpe ratio of the series

        Args:
            freq: Returns are converted to the same frequency before Sharpe ratio
                is compuated. Defaults to "M".
            risk_free: the risk free rate to use. Can be a float or a string. If is
                float, use the value as annualized risk free return. If is string,
                look for the corresponding DataFrame of risk free rate in
                ``self.risk_free``. ``self.risk_free`` can be set via the
                ``add_risk_free()`` class method. Defaults to 0.
            include_bm: whether to compute Sharpe ratio for benchmarks as well.
                Defaults to True.
            compound_method: method to use when compounding return.
                Defaults to "geometric".
            meta: whether to include meta data in output. Defaults to False.
                Available meta are:

                * freq: frequency of the series
                * risk_free: the risk free rate used
                * start: start date for calculating Sharpe ratio
                * end: end date for calculating Sharpe ratio

        Returns:
            pd.DataFrame: Sharpe ratio with the following columns

                * name: name of the series
                * field: name of the field. In this case, it is 'Sharpe ratio'
                    for all
                * value: Shapre ratio value

            Data described in meta will also be available in the returned DataFrame if
            meta is set to True.
        """

        # Convert series to the desired frequency
        ret = self.get_annualized_return(
            method=compound_method, include_bm=include_bm, meta=meta
        )
        vol = self.get_annualized_volatility(
            freq=freq, compound_method=compound_method, include_bm=include_bm, meta=True
        )

        # create risk free rate
        if isinstance(risk_free, str):
            try:
                rf = self.risk_free[risk_free]
            except KeyError:
                raise ValueError(f"Risk free rate is not set: risk_free={risk_free}")

            rf_by_series = []

            for i in range(len(vol)):
                rf = self._normalize_daterange(rf)
                rf = rf.get_annualized_return(method=compound_method, include_bm=False)
                rf = rf["value"][0]
        elif isinstance(risk_free, float) or isinstance(risk_free, int):
            rf = risk_free
        else:
            raise TypeError(
                "Risk free should be str, float, or int." f"Received: {type(risk_free)}"
            )

        result = ret
        result["value"] = (result["value"] - rf) / vol["value"]
        result["field"] = "sharpe ratio"

        return result
