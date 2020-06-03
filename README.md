# corm

Библиотека для создания ообьектных оберток над структурами данных и описания связей между ними

# мотивация

* сложно помнить ключи словарей, если структура данных большая
* организация связей между сущностями, особенно иерархических структурах данных
* возможность разделить безнес-логику и технические детали связывания сущностей друг с другом


# простая модель

```python
from corm import Storage, Model, Field


storage = Storage()

class User(Model):
    id: int = Field(pk=True)
    name: str

john = User({'id': 1, 'name': 'John'}, storage)

assert john.id == 1
assert john.name == 'John'
assert john.dict() == {'id': 1, 'name': 'John'}
assert storage.get(1, User) == john

# не обязательно описывать структуру данных 
```  
