"""Exercise the generated verifier's upload permissions without reading benchmark tests."""

import argparse
import asyncio
import stat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from workbuddy_bench.judge.runtime.harbor import HarborAttemptRuntime


class Environment:
    async def upload_dir(self,**kwargs):
        pass

    async def upload_file(self,source,target):
        self.mode=stat.S_IMODE(source.stat().st_mode)
        self.source=source


async def main(expected):
    env=Environment()
    verifier=SimpleNamespace(task=SimpleNamespace(paths=SimpleNamespace(tests_dir=Path("/unused"))))
    runtime=HarborAttemptRuntime(verifier,env,"/tests","/workspace","/logs/verifier",Path("/unused"))
    with patch("workbuddy_bench.judge.runtime.harbor.transform_verifier_file",return_value="pass\n"):
        await runtime.upload_tests()
    readable=bool(env.mode & stat.S_IROTH)
    assert readable==expected, (oct(env.mode),expected)
    assert not env.source.exists()
    print({"uploaded_mode":oct(env.mode),"nonroot_readable":readable,"temporary_file_removed":True})


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("--readable",choices=["yes","no"],required=True)
    ns=args.parse_args()
    asyncio.run(main(ns.readable=="yes"))
