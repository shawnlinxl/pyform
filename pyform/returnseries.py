import logging

log = logging.getLogger(__name__)

import copy
import math
import pandas as pd
from typing import Optional, Callable
from pyform.timeseries import TimeSeries


class ReturnSeries(TimeSeries):
    """A return series. It should be datetime indexed and
       has one column of returns data.
    """

    def __init__(self, df):

        super().__init__(df)

        self.benchmark = dict()

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
                    "benchmark": bm_names,
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
                data={"benchmark": bm_names, "field": "correlation", "value": corr}
            )

        return result

    def get_total_return(
        self,
        method: Optional[str] = "geometric",
        include_bm: Optional[bool] = True,
        meta: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Compute total return of the series

        Args:
            method: method to use when compounding total return.
                Defaults to "geometric".
            include_bm: whether to compute total return for benchmarks as well.
                Defaults to True.
            meta: whether to include meta data in output. Defaults to False.
                Available meta are:

                * method: method used to compound total return
                * start: start date for calculating correlation
                * end: end date for calculating correlation

        Returns:
            pd.DataFrame: total return results with the following columns

                * name: name of the series
                * field: name of the field. In this case, it is 'total return' for all
                * value: total return value, in decimals
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

        result = self.get_total_return(method=method, include_bm=include_bm, meta=True)
        result["field"] = "annualized return"
        result["days"] = (result["end"] - result["start"]) / pd.to_timedelta(
            1, unit="D"
        )

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
