import asyncio
import time
import numpy as np
import asyncpg
import ohmyfpg
import pandas as pd
import matplotlib.pyplot as plt


TEST_RUNS = 30
HEAT_RUNS = 3
DSN = 'postgres://postgres:postgres@localhost:5432/postgres'
QUERY = 'SELECT * FROM performance_test'


class Runner:

    name = ''

    def __init__(self, heat_runs, runs):
        self._heat_runs = heat_runs
        self._runs = runs

    async def connect(self, dsn):
        raise NotImplementedError()

    async def heat(self, conn, query):
        raise NotImplementedError()

    async def execute(self, conn, query):
        raise NotImplementedError()

    async def run(self, dsn, query):
        print('Connecting...')
        conn = await self.connect(dsn)
        print('Heating...')
        for i in range(self._heat_runs):
            await self.heat(conn, query)

        times = []
        print('Executing...')
        for i in range(self._runs):
            start = time.time()
            await self.execute(conn, query)
            end = time.time()
            times.append(round((end - start) * 1000))

        return (
            times,
            np.mean(times),
            np.min(times),
            np.percentile(times, 25),
            np.median(times),
            np.percentile(times, 75),
            np.max(times),
        )


class OhmyfpgRunner(Runner):

    name = 'ohmyfpg'

    async def connect(self, dsn):
        return await ohmyfpg.connect(dsn)

    async def heat(self, conn, query):
        await conn.fetch(query)

    async def execute(self, conn, query):
        return await conn.fetch(query)


class AsyncpgRunner(Runner):

    name = 'asyncpg'

    async def connect(self, dsn):
        return await asyncpg.connect(dsn)

    async def heat(self, conn, query):
        await conn.fetch(query)

    async def execute(self, conn, query):
        return await conn.fetch(query)


class OhmyfpgPandasRunner(OhmyfpgRunner):

    name = 'ohmyfpg-pandas'

    async def execute(self, conn, query):
        await conn.fetch(query)

    async def execute(self, conn, query):
        return pd.DataFrame(await super().execute(conn, query))


class AsyncpgPandasRunner(AsyncpgRunner):

    name = 'asyncpg-pandas'

    async def execute(self, conn, query):
        return pd.DataFrame([dict(r.items()) for r in
                             await super().execute(conn, query)])


async def main():
    runners = [
        OhmyfpgRunner(HEAT_RUNS, TEST_RUNS),
        AsyncpgRunner(HEAT_RUNS, TEST_RUNS),
        OhmyfpgPandasRunner(HEAT_RUNS, TEST_RUNS),
        AsyncpgPandasRunner(HEAT_RUNS, TEST_RUNS),
    ]
    results = {}
    for r in runners:
        print(f'Running test for {r.name}...')
        results[r.name] = await r.run(DSN, QUERY)

    boxplot_data = []
    boxplot_labels = []
    for name, stats in results.items():
        boxplot_data.append(stats[0])
        boxplot_labels.append(name)

        print('-' * 50)
        print(name)
        print(f'avg: {stats[1]}ms')
        print(f'min: {stats[2]}ms')
        print(f'p25: {stats[3]}ms')
        print(f'median: {stats[4]}ms')
        print(f'p75: {stats[5]}ms')
        print(f'max: {stats[6]}ms')
        print('-' * 50)

    fig, ax = plt.subplots()
    ax.set_title('Performance comparison (ms)')
    ax.boxplot(boxplot_data, labels=boxplot_labels)
    plt.savefig('performance-comparison.png')


if __name__ == '__main__':
    asyncio.run(main())
