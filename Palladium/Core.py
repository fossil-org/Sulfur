_refresh_in_progress = False

def SuccessMessage(o: "Plugin | str", pn: str | None = None) -> None:
    print(f"\033[32m{pn or "Palladium"} >> Refreshed {o if isinstance(o, str) else o.GetType().split(':')[1]}\033[0m")
def UnpackObject(node: "Object", visited: set[str] | None = None) -> "list['Object']":
    if visited is None:
        visited = set()
    
    node_path = node.GetPath()
    if node_path in visited:
        return []
    
    visited.add(node_path)
    l: "list['Object']" = []
    
    try:
        children: "list['Object']" = node.GetChildren()
        for child in children:
            l.extend(UnpackObject(child, visited))
    except Exception as e:
        print(f"\033[33mWarning: Could not get children for {node.GetType()}: {e}\033[0m")
    
    l.append(node)
    return l
def RefreshAll(node: "Object", sulfur: "ObjectTreeCLUI") -> None:
    global _refresh_in_progress
    
    if _refresh_in_progress:
        print(f"\033[33mTrigger already in progress, skipping nested call\033[0m")
        return
    
    _refresh_in_progress = True
    try:
        visited: set[str] = set()
        siblings: "list['Object'] | None" = node.GetSiblings()
        l: "list['Object']" = UnpackObject(node, visited)
        
        if siblings:
            for sibling in siblings:
                sibling_objects = UnpackObject(sibling, visited)
                l.extend([i for i in sibling_objects if ":" in i.GetType() and i.GetType().split(":")[1].startswith("$")])
        
        unique_objects: dict[str, "Object"] = {}
        for obj in l:
            unique_objects[obj.GetPath()] = obj
        l = list(unique_objects.values())
        
        filtered_objects = [obj for obj in l if not (":" in obj.GetType() and obj.GetType().split(":")[1] == "Trigger")]
        
        success_count = 0
        for obj in filtered_objects:
            try:
                obj._Execute(otclui=sulfur)
                success_count += 1
            except Exception as e:
                print(f"\033[31mFailed to refresh {obj.GetType()}: {e}\033[0m")
        
        SuccessMessage(f"{success_count}/{len(filtered_objects)} objects.")
    finally:
        _refresh_in_progress = False
