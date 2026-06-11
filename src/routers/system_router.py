from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any
import time
from ..graph.graph_coordinator import GraphCoordinator
from ..utils.logger import get_logger

router = APIRouter(prefix="/system", tags=["系统管理"])

coordinator = GraphCoordinator()
logger = get_logger("system_router")


class SystemConfig(BaseModel):
    """系统配置"""
    rewrite_enabled: bool = True


@router.get("/info")
async def get_system_info():
    """
    获取系统信息
    
    返回当前系统状态和配置信息
    """
    try:
        info = {
            "status": "running",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "version": "1.0.0",
            "available_agents": coordinator.get_available_agents(),
            "rewrite_enabled": coordinator.rewrite_enabled
        }
        return info
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.get("/config")
async def get_system_config():
    """
    获取当前系统配置
    """
    return {
        "rewrite_enabled": coordinator.rewrite_enabled
    }


@router.post("/config")
async def update_system_config(config: SystemConfig):
    """
    更新系统配置
    
    - **rewrite_enabled**: 是否启用问题重写功能
    """
    try:
        coordinator.rewrite_enabled = config.rewrite_enabled
        
        if config.rewrite_enabled:
            coordinator.question_rewriter.enable()
        else:
            coordinator.question_rewriter.disable()
        
        logger.info(f"系统配置已更新: rewrite_enabled={config.rewrite_enabled}")
        
        return {
            "message": "配置更新成功",
            "config": {
                "rewrite_enabled": coordinator.rewrite_enabled
            }
        }
    except Exception as e:
        logger.error(f"更新系统配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新系统配置失败: {str(e)}")


@router.post("/rewrite/toggle")
async def toggle_rewrite():
    """
    切换问题重写功能的启用/禁用状态
    """
    try:
        coordinator.rewrite_enabled = not coordinator.rewrite_enabled
        
        if coordinator.rewrite_enabled:
            coordinator.question_rewriter.enable()
            status = "enabled"
        else:
            coordinator.question_rewriter.disable()
            status = "disabled"
        
        logger.info(f"问题重写功能已{status}")
        
        return {
            "message": f"问题重写功能已{('启用' if coordinator.rewrite_enabled else '禁用')}",
            "rewrite_enabled": coordinator.rewrite_enabled
        }
    except Exception as e:
        logger.error(f"切换问题重写状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"切换问题重写状态失败: {str(e)}")


@router.post("/rewrite/test")
async def test_rewrite(question: str = Query(..., min_length=1, max_length=500)):
    """测试问题重写功能"""
    try:
        rewritten = await coordinator.question_rewriter.rewrite(question)
        
        return {
            "original": question,
            "rewritten": rewritten,
            "changed": rewritten != question
        }
    except Exception as e:
        logger.error(f"测试问题重写失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试问题重写失败: {str(e)}")
