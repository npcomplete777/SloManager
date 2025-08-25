# async_utils.py
import asyncio
import streamlit as st
from typing import List, Coroutine, Any

# --- CONFIGURATION ---
# The maximum number of API calls to run concurrently.
# Adjust this value down if you still see rate-limiting errors.
MAX_CONCURRENT_TASKS = 2


async def _run_tasks_with_progress(tasks: List[Coroutine]) -> List[Any]:
    """Runs tasks concurrently with a semaphore to limit concurrency."""
    results = [None] * len(tasks)  # Use a pre-sized list to store results in order
    total_tasks = len(tasks)
    progress_bar = st.progress(0, text="Executing API calls...")
    completed_count = 0

    # Create a semaphore to limit concurrency to MAX_CONCURRENT_TASKS
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    async def task_wrapper(task: Coroutine, index: int):
        """Wrapper to acquire semaphore, run task, capture result, and update progress."""
        nonlocal completed_count
        async with semaphore:
            try:
                result = await task
                results[index] = result
            except Exception as e:
                # Store exception to handle it later
                results[index] = e
            finally:
                completed_count += 1
                # Update progress
                progress_value = completed_count / total_tasks
                progress_text = f"Executing API calls... ({completed_count}/{total_tasks})"
                progress_bar.progress(progress_value, text=progress_text)

    # Create wrapped tasks
    wrapped_tasks = [task_wrapper(task, i) for i, task in enumerate(tasks)]

    # Run all wrapped tasks
    await asyncio.gather(*wrapped_tasks)

    progress_bar.empty()  # Clear the progress bar
    return results


def run_async_tasks(tasks: List[Coroutine]) -> List[Any]:
    """
    Public function to run a list of async tasks from a sync context.
    """
    return asyncio.run(_run_tasks_with_progress(tasks))