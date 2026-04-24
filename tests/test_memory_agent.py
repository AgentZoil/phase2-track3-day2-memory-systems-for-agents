from memory_agent import build_memory_graph
from memory_agent.agent import MultiMemoryAgent


def test_profile_conflict_update_prefers_latest_fact():
    agent = MultiMemoryAgent()

    agent.invoke("Tôi dị ứng sữa bò.")
    result = agent.invoke("À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.")

    assert agent.store.profile.facts["allergy"] == "đậu nành"
    assert "đậu nành" in result["assistant_message"] or "bộ nhớ" in result["assistant_message"].lower()


def test_profile_stores_multiple_facts():
    agent = MultiMemoryAgent()

    agent.invoke("My name is Linh.")
    agent.invoke("I live in Hanoi.")

    assert agent.store.profile.facts["name"] == "Linh"
    assert agent.store.profile.facts["location"] == "Hanoi"


def test_prompt_includes_memory_sections():
    agent = MultiMemoryAgent()
    payload = agent.invoke("My name is Linh.")

    prompt = payload["prompt"]
    assert "Bộ nhớ hồ sơ:" in prompt
    assert "Bộ nhớ sự kiện:" in prompt
    assert "Bộ nhớ ngữ nghĩa:" in prompt
    assert "Đoạn hội thoại gần đây:" in prompt


def test_semantic_memory_retrieval_is_used():
    agent = MultiMemoryAgent()
    agent.store.semantic.add_chunk(
        "faq-1",
        "Use docker compose service name when the container cannot be resolved.",
        tags=["docker", "compose"],
    )

    payload = agent.invoke("What should I check for docker service resolution?")

    assert "ghi chú liên quan" in payload["assistant_message"].lower()


def test_episode_is_recorded_when_task_completes():
    agent = MultiMemoryAgent()
    agent.invoke("Task done: fixed the deployment issue.")

    assert agent.store.episodic.episodes


def test_graph_entrypoint_invokes_successfully():
    graph = build_memory_graph()
    result = graph.invoke("My name is Linh.")

    assert result["assistant_message"]
    assert "prompt" in result
    assert result["route"] == "profile"
    assert "profile" in result["selected_memory_types"]


def test_graph_routes_semantic_queries_to_semantic_scope():
    graph = build_memory_graph()
    graph.agent.store.semantic.add_chunk(
        "faq-2",
        "Use docker compose service name when the container cannot be resolved.",
        tags=["docker", "compose"],
    )

    result = graph.invoke("What should I check for docker service resolution?")

    assert result["route"] == "semantic"
    assert "semantic" in result["selected_memory_types"]
    assert "Phạm vi truy xuất:" in result["prompt"]


def test_question_turn_does_not_overwrite_profile_fact():
    agent = MultiMemoryAgent()
    agent.invoke("Tôi dị ứng sữa bò.")
    agent.invoke("Tôi dị ứng gì?")

    assert agent.store.profile.facts["allergy"] == "sữa bò"
