"""
竞态条件专项测试 - 模拟并验证潜在的并发问题
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, "/home/galio/repos/project3/smiger-bot/backend")

from app.core.conversation import ConversationManager
from app.models.database import Conversation


class TestRaceConditions:
    """竞态条件测试套件"""

    @pytest.mark.asyncio
    async def test_turn_count_race_condition(self):
        """
        测试场景：同一会话的 turn_count 并发更新
        预期问题：多个并行请求可能导致 turn_count 少增
        """
        print("\n[竞态测试] turn_count 并发更新...")

        # 模拟数据库会话
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        # 创建测试会话
        conv = Conversation(
            id="test_race_001",
            visitor_id="visitor_001",
            language="zh",
            turn_count=0
        )

        # 模拟 handle_message 中的竞态
        # 假设3个请求同时读取 turn_count=0，然后都+1，结果应该是3但实际可能都是1

        async def simulate_message_processing(conv, delay=0):
            """模拟消息处理"""
            await asyncio.sleep(delay)

            # 读取当前值 (模拟多个请求同时读到0)
            current = conv.turn_count

            # 模拟处理时间
            await asyncio.sleep(0.1)

            # 写入 (可能覆盖其他请求的更新)
            conv.turn_count = current + 1

            return conv.turn_count

        # 并发执行3次
        tasks = [
            simulate_message_processing(conv, delay=0),
            simulate_message_processing(conv, delay=0.01),
            simulate_message_processing(conv, delay=0.02),
        ]

        results = await asyncio.gather(*tasks)

        print(f"  3次请求返回的turn_count: {results}")
        print(f"  最终turn_count: {conv.turn_count} (期望=3)")

        # 验证是否存在竞态
        if conv.turn_count != 3:
            print(f"  ⚠️ 竞态条件确认！期望值=3，实际={conv.turn_count}")
            assert False, f"竞态条件: turn_count={conv.turn_count}, 期望=3"
        else:
            print("  ✅ 无竞态问题")

    @pytest.mark.asyncio
    async def test_handoff_race_condition(self):
        """
        测试场景：转人工状态并发触发
        预期问题：多个请求可能都触发转人工通知
        """
        print("\n[竞态测试] handoff 并发触发...")

        conv = Conversation(
            id="test_handoff_001",
            visitor_id="visitor_001",
            language="zh",
            handoff_status="none",
            turn_count=5
        )

        trigger_count = 0

        async def check_and_trigger_handoff(conv, delay=0):
            """模拟转人工检查"""
            nonlocal trigger_count
            await asyncio.sleep(delay)

            # 检查条件
            if conv.handoff_status in ("none", "resolved"):
                # 模拟处理延迟
                await asyncio.sleep(0.05)

                # 再次检查并设置（典型的TOCTOU问题）
                if conv.handoff_status in ("none", "resolved"):
                    conv.handoff_status = "pending"
                    conv.handoff_at = datetime.now(timezone.utc)
                    trigger_count += 1
                    return True
            return False

        # 模拟3个请求同时检测到购买意向
        tasks = [
            check_and_trigger_handoff(conv, delay=0),
            check_and_trigger_handoff(conv, delay=0.01),
            check_and_trigger_handoff(conv, delay=0.02),
        ]

        results = await asyncio.gather(*tasks)

        print(f"  触发转人工的次数: {trigger_count} (期望=1)")
        print(f"  各请求结果: {results}")

        if trigger_count > 1:
            print(f"  ⚠️ 竞态条件确认！转人工被触发{trigger_count}次")
            assert False, f"handoff竞态: 触发{trigger_count}次，期望1次"
        else:
            print("  ✅ 无竞态问题")

    @pytest.mark.asyncio
    async def test_redis_history_race(self):
        """
        测试场景：Redis历史记录并发读写
        预期问题：消息可能丢失或乱序
        """
        print("\n[竞态测试] Redis历史记录并发读写...")

        # 模拟Redis
        fake_redis = {"conv:test:history": "[]"}

        async def read_history():
            await asyncio.sleep(0.001)
            import json
            return json.loads(fake_redis.get("conv:test:history", "[]"))

        async def save_history(history):
            await asyncio.sleep(0.001)
            import json
            fake_redis["conv:test:history"] = json.dumps(history)

        async def add_message(message, delay=0):
            """模拟添加消息到历史"""
            await asyncio.sleep(delay)

            # 读取历史
            history = await read_history()

            # 模拟处理延迟（制造竞态窗口）
            await asyncio.sleep(0.02)

            # 添加新消息
            history.append({"role": "user", "content": message})

            # 保存
            await save_history(history)

            return len(history)

        # 并发添加3条消息
        tasks = [
            add_message("消息1", delay=0),
            add_message("消息2", delay=0.005),
            add_message("消息3", delay=0.010),
        ]

        results = await asyncio.gather(*tasks)

        # 检查结果
        final_history = await read_history()

        print(f"  各任务返回的历史长度: {results}")
        print(f"  最终历史消息数: {len(final_history)} (期望=3)")
        print(f"  消息内容: {[m['content'] for m in final_history]}")

        if len(final_history) != 3:
            print(f"  ⚠️ 竞态条件确认！消息丢失")
            assert False, f"消息丢失: 期望3条，实际{len(final_history)}条"
        else:
            print("  ✅ 无竞态问题")

    @pytest.mark.asyncio
    async def test_websocket_registry_race(self):
        """
        测试场景：WebSocket连接注册竞态
        预期问题：同一conversation_id的多个连接可能相互覆盖
        """
        print("\n[竞态测试] WebSocket注册覆盖...")

        # 模拟ws_registry
        connections = {}

        def register(conv_id, ws_id):
            """注册连接（原始实现，无锁）"""
            connections[conv_id] = ws_id
            return True

        async def simulate_connect(conv_id, ws_id, delay=0):
            await asyncio.sleep(delay)
            register(conv_id, ws_id)
            return connections.get(conv_id)

        conv_id = "test_conv_001"

        # 同一用户开两个标签页
        tasks = [
            simulate_connect(conv_id, "ws_tab_1", delay=0),
            simulate_connect(conv_id, "ws_tab_2", delay=0.01),
        ]

        results = await asyncio.gather(*tasks)

        print(f"  Tab1注册后查询: {results[0]}")
        print(f"  Tab2注册后查询: {results[1]}")
        print(f"  最终连接归属: {connections.get(conv_id)}")

        # 验证问题
        if results[0] != "ws_tab_1":
            print(f"  ⚠️ Tab1的连接被覆盖！")
            assert False, "WebSocket注册覆盖竞态确认"
        else:
            print("  ✅ 无覆盖问题")


class TestPerformanceBottlenecks:
    """性能瓶颈测试"""

    @pytest.mark.asyncio
    async def test_chroma_db_query_bottleneck(self):
        """
        测试场景：ChromaDB向量搜索并发性能
        预期瓶颈：ChromaDB使用文件锁，高并发时可能串行化
        """
        print("\n[性能测试] ChromaDB并发查询...")

        async def mock_chroma_query(query_id, delay=0.1):
            """模拟ChromaDB查询"""
            await asyncio.sleep(delay)  # 模拟查询耗时
            return {"results": f"result_{query_id}"}

        # 串行执行10次
        start = asyncio.get_event_loop().time()
        for i in range(10):
            await mock_chroma_query(i)
        serial_time = asyncio.get_event_loop().time() - start

        # 并行执行10次
        start = asyncio.get_event_loop().time()
        await asyncio.gather(*[mock_chroma_query(i) for i in range(10)])
        parallel_time = asyncio.get_event_loop().time() - start

        print(f"  串行执行10次: {serial_time:.2f}s")
        print(f"  并行执行10次: {parallel_time:.2f}s")
        print(f"  加速比: {serial_time/parallel_time:.1f}x")

        # 如果加速比接近1，说明存在串行瓶颈
        if parallel_time > serial_time * 0.8:
            print(f"  ⚠️ 可能存在串行瓶颈！")

    @pytest.mark.asyncio
    async def test_llm_gateway_bottleneck(self):
        """
        测试场景：LLM网关并发限制
        预期瓶颈：API有rate limit或连接池限制
        """
        print("\n[性能测试] LLM网关并发请求...")

        semaphore = asyncio.Semaphore(5)  # 模拟连接池限制

        async def mock_llm_call(req_id):
            async with semaphore:
                await asyncio.sleep(0.2)  # 模拟LLM调用
                return f"response_{req_id}"

        start = asyncio.get_event_loop().time()
        await asyncio.gather(*[mock_llm_call(i) for i in range(20)])
        elapsed = asyncio.get_event_loop().time() - start

        print(f"  20个请求总耗时: {elapsed:.2f}s (理论最小: 0.8s)")
        print(f"  吞吐率: {20/elapsed:.1f} req/s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
