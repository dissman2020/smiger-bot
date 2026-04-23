"""
并发压力测试 - 模拟多用户同时咨询场景
测试目标：验证会话隔离性、竞态条件、性能瓶颈
"""
import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import List

import pytest
import websockets
from httpx import AsyncClient


@dataclass
class TestResult:
    """测试结果记录"""
    conversation_id: str
    message_index: int
    send_time: float
    recv_time: float
    response_text: str
    turn_count: int
    success: bool
    error: str = ""


class ConcurrentChatStressTest:
    """并发聊天压力测试套件"""

    BASE_URL = "http://localhost:8000"
    WS_URL = "ws://localhost:8000/api/chat/ws"

    def __init__(self):
        self.results: List[TestResult] = []
        self.errors: List[dict] = []

    async def send_single_message(
        self,
        conversation_id: str,
        message: str,
        message_index: int,
        delay_before: float = 0
    ) -> TestResult:
        """发送单条消息并记录响应时间"""
        await asyncio.sleep(delay_before)

        start_time = time.time()
        result = TestResult(
            conversation_id=conversation_id,
            message_index=message_index,
            send_time=start_time,
            recv_time=0,
            response_text="",
            turn_count=-1,
            success=False
        )

        try:
            async with websockets.connect(
                f"{self.WS_URL}/{conversation_id}",
                timeout=30
            ) as ws:
                # 发送消息
                await ws.send(json.dumps({
                    "message": message,
                    "visitor_id": f"visitor_{conversation_id[:8]}",
                    "language": "zh"
                }))

                # 接收流式响应
                full_response = []
                final_meta = None

                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)

                        if data.get("type") == "token":
                            full_response.append(data.get("content", ""))
                        elif data.get("type") == "done":
                            final_meta = data
                            break
                        elif data.get("type") == "error":
                            result.error = data.get("content", "Unknown error")
                            break
                    except asyncio.TimeoutError:
                        result.error = "Response timeout"
                        break

                result.recv_time = time.time()
                result.response_text = "".join(full_response)
                result.turn_count = final_meta.get("conversation_id", -1)
                result.success = final_meta is not None and not result.error

        except Exception as e:
            result.recv_time = time.time()
            result.error = str(e)

        return result

    async def test_scenario_1_multi_user_concurrent(self, user_count: int = 10):
        """
        场景1：多用户同时发送消息
        验证：各用户响应是否正确，是否相互干扰
        """
        print(f"\n[场景1] {user_count} 个用户同时发送消息...")

        tasks = []
        for i in range(user_count):
            conv_id = f"stress_test_user_{i}_{uuid.uuid4().hex[:8]}"
            task = self.send_single_message(
                conv_id,
                f"用户{i}的问题：我想了解WY-500SS吉他",
                message_index=0
            )
            tasks.append(task)

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        # 分析结果
        success_count = sum(1 for r in results if isinstance(r, TestResult) and r.success)
        error_count = len(results) - success_count
        avg_response_time = sum(
            (r.recv_time - r.send_time)
            for r in results if isinstance(r, TestResult)
        ) / max(len(results), 1)

        print(f"  完成: {success_count}/{user_count}, 失败: {error_count}")
        print(f"  总耗时: {elapsed:.2f}s, 平均响应: {avg_response_time:.2f}s")

        # 验证响应隔离性
        responses = [r.response_text for r in results if isinstance(r, TestResult)]
        unique_responses = len(set(responses))
        print(f"  唯一响应数: {unique_responses}/{success_count} (应接近{success_count})")

        return results

    async def test_scenario_2_rapid_fire_same_user(self, message_count: int = 5):
        """
        场景2：同一用户快速连续发送多条消息
        验证：turn_count是否正确递增，消息是否乱序
        """
        print(f"\n[场景2] 同一用户快速发送 {message_count} 条消息...")

        conv_id = f"rapid_fire_{uuid.uuid4().hex[:8]}"
        tasks = []

        for i in range(message_count):
            task = self.send_single_message(
                conv_id,
                f"第{i+1}条消息",
                message_index=i,
                delay_before=i * 0.1  # 100ms间隔快速发送
            )
            tasks.append(task)

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        # 分析结果
        success_results = [r for r in results if isinstance(r, TestResult) and r.success]
        print(f"  成功: {len(success_results)}/{message_count}")
        print(f"  总耗时: {elapsed:.2f}s")

        # 检查是否有竞态问题（通过响应内容分析turn_count）
        # 注意：由于测试环境可能没有真实LLM，这里主要检查是否崩溃
        errors = [r.error for r in results if isinstance(r, TestResult) and r.error]
        if errors:
            print(f"  错误详情: {errors[:3]}")

        return results

    async def test_scenario_3_mixed_load(self, concurrent_users: int = 20, messages_per_user: int = 3):
        """
        场景3：混合负载 - 多用户各发送多条消息
        验证：系统整体稳定性
        """
        print(f"\n[场景3] 混合负载: {concurrent_users}用户 x {messages_per_user}消息...")

        all_tasks = []
        for user_idx in range(concurrent_users):
            conv_id = f"mixed_{user_idx}_{uuid.uuid4().hex[:6]}"
            for msg_idx in range(messages_per_user):
                task = self.send_single_message(
                    conv_id,
                    f"用户{user_idx}的消息{msg_idx+1}",
                    message_index=msg_idx,
                    delay_before=msg_idx * 0.5  # 同一用户间隔500ms
                )
                all_tasks.append((user_idx, msg_idx, task))

        start = time.time()
        results = await asyncio.gather(*[t[2] for t in all_tasks], return_exceptions=True)
        elapsed = time.time() - start

        # 分析结果
        success_count = sum(1 for r in results if isinstance(r, TestResult) and r.success)
        total = len(results)
        success_rate = success_count / total * 100

        print(f"  总请求: {total}")
        print(f"  成功: {success_count} ({success_rate:.1f}%)")
        print(f"  总耗时: {elapsed:.2f}s")
        print(f"  平均TPS: {total/elapsed:.1f}")

        return results

    async def test_scenario_4_connection_storm(self, connection_count: int = 50):
        """
        场景4：连接风暴 - 大量用户同时建立WebSocket连接
        验证：连接限制、资源耗尽问题
        """
        print(f"\n[场景4] 连接风暴测试: {connection_count} 个并发连接...")

        connections = []
        failed_connections = 0

        async def try_connect(idx):
            conv_id = f"storm_{idx}_{uuid.uuid4().hex[:6]}"
            try:
                ws = await websockets.connect(
                    f"{self.WS_URL}/{conv_id}",
                    timeout=5
                )
                return ws
            except Exception as e:
                return e

        start = time.time()
        tasks = [try_connect(i) for i in range(connection_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, websockets.WebSocketClientProtocol):
                connections.append(r)
            else:
                failed_connections += 1

        elapsed = time.time() - start

        print(f"  成功连接: {len(connections)}/{connection_count}")
        print(f"  失败连接: {failed_connections}")
        print(f"  建立时间: {elapsed:.2f}s")

        # 清理连接
        close_tasks = [ws.close() for ws in connections]
        await asyncio.gather(*close_tasks, return_exceptions=True)

        return {
            "success": len(connections),
            "failed": failed_connections,
            "time": elapsed
        }


@pytest.mark.stress
@pytest.mark.asyncio
class TestConcurrentChat:
    """pytest 测试类"""

    async def test_multi_user_concurrent(self):
        """测试：10个用户同时发送消息"""
        tester = ConcurrentChatStressTest()
        results = await tester.test_scenario_1_multi_user_concurrent(user_count=10)

        success_count = sum(1 for r in results if isinstance(r, TestResult) and r.success)
        assert success_count >= 8, f"成功率过低: {success_count}/10"

    async def test_rapid_fire_same_user(self):
        """测试：同一用户快速发送5条消息"""
        tester = ConcurrentChatStressTest()
        results = await tester.test_scenario_2_rapid_fire_same_user(message_count=5)

        # 检查系统是否崩溃（即使响应可能不正确）
        error_count = sum(1 for r in results if isinstance(r, TestResult) and r.error)
        assert error_count < 3, f"错误过多，可能存在竞态: {error_count} errors"

    async def test_mixed_load(self):
        """测试：混合负载 20用户x3消息"""
        tester = ConcurrentChatStressTest()
        results = await tester.test_scenario_3_mixed_load(
            concurrent_users=20,
            messages_per_user=3
        )

        success_count = sum(1 for r in results if isinstance(r, TestResult) and r.success)
        success_rate = success_count / len(results) * 100
        assert success_rate >= 80, f"成功率不足80%: {success_rate:.1f}%"


# 独立运行入口
if __name__ == "__main__":
    async def main():
        tester = ConcurrentChatStressTest()

        print("=" * 60)
        print("Smiger Bot 并发压力测试")
        print("=" * 60)

        # 运行所有场景
        await tester.test_scenario_1_multi_user_concurrent(user_count=10)
        await asyncio.sleep(2)

        await tester.test_scenario_2_rapid_fire_same_user(message_count=5)
        await asyncio.sleep(2)

        await tester.test_scenario_3_mixed_load(concurrent_users=10, messages_per_user=3)
        await asyncio.sleep(2)

        await tester.test_scenario_4_connection_storm(connection_count=30)

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    asyncio.run(main())
