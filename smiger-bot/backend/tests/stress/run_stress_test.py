#!/usr/bin/env python3
"""
压力测试运行器 - 执行并发场景测试并生成报告
用法: python run_stress_test.py [--scenario 1|2|3|4|all]
"""
import asyncio
import argparse
import json
import time
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/galio/repos/project3/smiger-bot/backend")


@dataclass
class StressTestReport:
    """压力测试报告"""
    scenario_name: str
    total_requests: int
    success_count: int
    failure_count: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    errors: List[str]
    timestamp: str


class MockStressTester:
    """
    模拟压力测试器（无需完整后端环境）
    用于演示并发问题的模拟测试
    """

    def __init__(self):
        self.reports: List[StressTestReport] = []
        # 模拟共享状态
        self.shared_turn_count = 0
        self.shared_handoff_triggered = False
        self.handoff_trigger_count = 0

    async def simulate_message_processing(self, conv_id: str, msg_idx: int) -> Dict[str, Any]:
        """模拟消息处理过程，包含竞态条件"""
        start = time.time()

        # 模拟网络延迟
        await asyncio.sleep(0.05)

        # 模拟读取数据库（竞态点1：读取turn_count）
        current_turn = self.shared_turn_count

        # 模拟处理时间（增加竞态窗口）
        await asyncio.sleep(0.1)

        # 模拟写入数据库（竞态点2：写入turn_count）
        # 问题：如果两个请求同时读取到相同的current_turn，后写入的会覆盖前者
        self.shared_turn_count = current_turn + 1

        # 模拟handoff检查（竞态点3）
        if not self.shared_handoff_triggered:
            await asyncio.sleep(0.02)  # 竞态窗口
            if not self.shared_handoff_triggered:
                self.shared_handoff_triggered = True
                self.handoff_trigger_count += 1

        elapsed = time.time() - start

        return {
            "conv_id": conv_id,
            "msg_idx": msg_idx,
            "success": True,
            "response_time": elapsed,
            "observed_turn_count": self.shared_turn_count
        }

    async def run_scenario_1_multi_user(self, user_count: int = 10) -> StressTestReport:
        """场景1: 多用户并发（无竞态，每个用户独立）"""
        print(f"\n{'='*60}")
        print(f"场景1: {user_count}个用户同时发送消息")
        print(f"{'='*60}")

        start_time = time.time()

        # 每个用户有自己的turn_count
        user_turn_counts = {}

        async def user_session(user_id: int):
            user_turn_counts[user_id] = 0
            await asyncio.sleep(0.05)  # 网络延迟
            current = user_turn_counts[user_id]
            await asyncio.sleep(0.1)   # 处理时间
            user_turn_counts[user_id] = current + 1
            return {"user_id": user_id, "turn_count": user_turn_counts[user_id]}

        tasks = [user_session(i) for i in range(user_count)]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # 验证每个用户的turn_count都是1
        errors = []
        for r in results:
            if r["turn_count"] != 1:
                errors.append(f"用户{r['user_id']}的turn_count={r['turn_count']}, 期望=1")

        report = StressTestReport(
            scenario_name="多用户并发（场景1）",
            total_requests=user_count,
            success_count=user_count - len(errors),
            failure_count=len(errors),
            avg_response_time=elapsed,
            max_response_time=elapsed,
            min_response_time=elapsed,
            errors=errors,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        self._print_report(report)
        return report

    async def run_scenario_2_same_user_rapid(self, message_count: int = 5) -> StressTestReport:
        """场景2: 同一用户快速发送多条消息（存在竞态）"""
        print(f"\n{'='*60}")
        print(f"场景2: 同一用户快速发送{message_count}条消息")
        print(f"{'='*60}")
        print("预期问题: turn_count可能因竞态而少增")

        self.shared_turn_count = 0
        self.shared_handoff_triggered = False
        self.handoff_trigger_count = 0

        start_time = time.time()

        # 模拟同一用户的多个请求并发
        tasks = [
            self.simulate_message_processing("same_user", i)
            for i in range(message_count)
        ]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # 分析竞态结果
        errors = []
        expected_turn = message_count
        actual_turn = self.shared_turn_count

        if actual_turn != expected_turn:
            errors.append(
                f"竞态条件确认！期望turn_count={expected_turn}, 实际={actual_turn}"
            )

        if self.handoff_trigger_count > 1:
            errors.append(
                f"handoff竞态！触发{self.handoff_trigger_count}次，期望1次"
            )

        response_times = [r["response_time"] for r in results]

        report = StressTestReport(
            scenario_name="同一用户快速发送（场景2）",
            total_requests=message_count,
            success_count=message_count,
            failure_count=0,
            avg_response_time=sum(response_times)/len(response_times),
            max_response_time=max(response_times),
            min_response_time=min(response_times),
            errors=errors,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        print(f"  期望turn_count: {expected_turn}")
        print(f"  实际turn_count: {actual_turn}")
        print(f"  handoff触发次数: {self.handoff_trigger_count}")
        self._print_report(report)
        return report

    async def run_scenario_3_mixed_load(
        self,
        concurrent_users: int = 10,
        messages_per_user: int = 3
    ) -> StressTestReport:
        """场景3: 混合负载测试"""
        print(f"\n{'='*60}")
        print(f"场景3: 混合负载 ({concurrent_users}用户 x {messages_per_user}消息)")
        print(f"{'='*60}")

        total_requests = concurrent_users * messages_per_user
        start_time = time.time()

        # 模拟不同用户
        async def user_flow(user_id: int):
            turn_count = 0
            for msg_idx in range(messages_per_user):
                await asyncio.sleep(0.01)  # 用户思考时间
                current = turn_count
                await asyncio.sleep(0.05)   # 处理
                turn_count = current + 1
            return {"user_id": user_id, "final_turn": turn_count}

        tasks = [user_flow(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # 验证每个用户的消息数正确
        errors = []
        for r in results:
            if r["final_turn"] != messages_per_user:
                errors.append(
                    f"用户{r['user_id']}最终turn={r['final_turn']}, 期望={messages_per_user}"
                )

        report = StressTestReport(
            scenario_name="混合负载（场景3）",
            total_requests=total_requests,
            success_count=concurrent_users - len(errors),
            failure_count=len(errors),
            avg_response_time=elapsed / concurrent_users,
            max_response_time=elapsed,
            min_response_time=elapsed,
            errors=errors,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        self._print_report(report)
        return report

    async def run_scenario_4_connection_pool(
        self, connection_count: int = 20
    ) -> StressTestReport:
        """场景4: 连接池耗尽测试"""
        print(f"\n{'='*60}")
        print(f"场景4: 连接池压力测试 ({connection_count}并发)")
        print(f"{'='*60}")

        # 模拟数据库连接池限制
        connection_pool_size = 5
        pool_semaphore = asyncio.Semaphore(connection_pool_size)
        active_connections = 0
        max_active = 0

        async def acquire_connection(conn_id: int):
            nonlocal active_connections, max_active
            async with pool_semaphore:
                active_connections += 1
                max_active = max(max_active, active_connections)
                await asyncio.sleep(0.1)  # 模拟连接使用
                active_connections -= 1
                return conn_id

        start_time = time.time()
        tasks = [acquire_connection(i) for i in range(connection_count)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        print(f"  连接池大小: {connection_pool_size}")
        print(f"  最大并发连接: {max_active}")
        print(f"  总耗时: {elapsed:.2f}s")
        print(f"  理论最小耗时: {connection_count * 0.1 / connection_pool_size:.2f}s")

        report = StressTestReport(
            scenario_name="连接池压力（场景4）",
            total_requests=connection_count,
            success_count=connection_count,
            failure_count=0,
            avg_response_time=elapsed / connection_count,
            max_response_time=elapsed,
            min_response_time=0.1,
            errors=[],
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        self._print_report(report)
        return report

    def _print_report(self, report: StressTestReport):
        """打印测试报告"""
        print(f"\n  测试结果:")
        print(f"    总请求数: {report.total_requests}")
        print(f"    成功: {report.success_count}")
        print(f"    失败: {report.failure_count}")
        print(f"    平均响应时间: {report.avg_response_time:.3f}s")
        print(f"    最大响应时间: {report.max_response_time:.3f}s")

        if report.errors:
            print(f"\n  ⚠️ 发现的问题:")
            for err in report.errors[:5]:
                print(f"    - {err}")
            if len(report.errors) > 5:
                print(f"    ... 还有 {len(report.errors) - 5} 个问题")
        else:
            print(f"\n  ✅ 未发现明显问题")

    def generate_summary(self) -> str:
        """生成测试摘要"""
        summary = []
        summary.append("\n" + "="*60)
        summary.append("压力测试摘要")
        summary.append("="*60)

        total_issues = sum(len(r.errors) for r in self.reports)

        for report in self.reports:
            status = "⚠️" if report.errors else "✅"
            summary.append(
                f"{status} {report.scenario_name}: "
                f"成功{report.success_count}/{report.total_requests}, "
                f"问题{len(report.errors)}个"
            )

        summary.append(f"\n总计发现问题: {total_issues} 个")

        if total_issues > 0:
            summary.append("\n建议:")
            summary.append("1. 为turn_count更新添加数据库级乐观锁")
            summary.append("2. 为handoff状态转换添加分布式锁")
            summary.append("3. 为WebSocket注册添加连接存在性检查")
            summary.append("4. 监控ChromaDB查询延迟，考虑缓存优化")

        return "\n".join(summary)


async def main():
    parser = argparse.ArgumentParser(description="Smiger Bot 压力测试")
    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        help="测试场景: 1=多用户, 2=单用户快速, 3=混合负载, 4=连接池, all=全部"
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="用户数量（场景1,3）"
    )
    parser.add_argument(
        "--messages",
        type=int,
        default=5,
        help="每用户消息数（场景2,3）"
    )

    args = parser.parse_args()

    tester = MockStressTester()

    if args.scenario in ("1", "all"):
        report = await tester.run_scenario_1_multi_user(args.users)
        tester.reports.append(report)

    if args.scenario in ("2", "all"):
        report = await tester.run_scenario_2_same_user_rapid(args.messages)
        tester.reports.append(report)

    if args.scenario in ("3", "all"):
        report = await tester.run_scenario_3_mixed_load(args.users, args.messages)
        tester.reports.append(report)

    if args.scenario in ("4", "all"):
        report = await tester.run_scenario_4_connection_pool(args.users * 2)
        tester.reports.append(report)

    # 打印摘要
    print(tester.generate_summary())

    # 保存详细报告
    report_file = f"stress_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump([asdict(r) for r in tester.reports], f, indent=2)
    print(f"\n详细报告已保存: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
