from pydantic import BaseModel, HttpUrl

class PaperCategory(BaseModel):
    count: int = 0
    name: str = ""

    
class Papers(BaseModel):
    ai: PaperCategory = PaperCategory(name="Artificial intelligence")
    vision: PaperCategory = PaperCategory(name="Computer vision")
    mlmining: PaperCategory = PaperCategory(name="Machine Learning")
    nlp: PaperCategory = PaperCategory(name="Natural language processing")
    inforet: PaperCategory = PaperCategory(name="The Web & information retrieval")
    arch: PaperCategory = PaperCategory(name="Computer architecture")
    comm: PaperCategory = PaperCategory(name="Computer networks")
    sec: PaperCategory = PaperCategory(name="Computer security")
    mod: PaperCategory = PaperCategory(name="Databases")
    da: PaperCategory = PaperCategory(name="Design automation")
    bed: PaperCategory = PaperCategory(name="Embedded & real-time systems")
    hpc: PaperCategory = PaperCategory(name="High performance computing")
    mobile: PaperCategory = PaperCategory(name="Mobile computing")
    metrics: PaperCategory = PaperCategory(name="Measurement & perf. analysiss")
    ops: PaperCategory = PaperCategory(name="Operating systems")
    plan: PaperCategory = PaperCategory(name="Programming languages")
    soft: PaperCategory = PaperCategory(name="Software engineering")
    act: PaperCategory = PaperCategory(name="Algorithms and complexity")
    crypt: PaperCategory = PaperCategory(name="Cryptography")
    log: PaperCategory = PaperCategory(name="Logic & verification")
    graph: PaperCategory = PaperCategory(name="Computer graphics")
    bio: PaperCategory = PaperCategory(name="Computational biology & bioinformatics")
    csed: PaperCategory = PaperCategory(name="Computer science education")
    ecom: PaperCategory = PaperCategory(name="Economics & computation")
    chi: PaperCategory = PaperCategory(name="Human-computer interaction")
    robotics: PaperCategory = PaperCategory(name="Robotics")
    visualization: PaperCategory = PaperCategory(name="visualization")

class Advisor(BaseModel):
    name: str
    # href: HttpUrl
    href: str
    papers: Papers
    raw_content: dict = {}

class Rankings(BaseModel):
    ai: PaperCategory = PaperCategory(name="Artificial intelligence")
    vision: PaperCategory = PaperCategory(name="Computer vision")
    mlmining: PaperCategory = PaperCategory(name="Machine Learning")
    nlp: PaperCategory = PaperCategory(name="Natural language processing")
    inforet: PaperCategory = PaperCategory(name="The Web & information retrieval")
    arch: PaperCategory = PaperCategory(name="Computer architecture")
    comm: PaperCategory = PaperCategory(name="Computer networks")
    sec: PaperCategory = PaperCategory(name="Computer security")
    mod: PaperCategory = PaperCategory(name="Databases")
    da: PaperCategory = PaperCategory(name="Design automation")
    bed: PaperCategory = PaperCategory(name="Embedded & real-time systems")
    hpc: PaperCategory = PaperCategory(name="High performance computing")
    mobile: PaperCategory = PaperCategory(name="Mobile computing")
    metrics: PaperCategory = PaperCategory(name="Measurement & perf. analysis")
    ops: PaperCategory = PaperCategory(name="Operating systems")
    plan: PaperCategory = PaperCategory(name="Programming languages")
    soft: PaperCategory = PaperCategory(name="Software engineering")
    act: PaperCategory = PaperCategory(name="Algorithms and complexity")
    crypt: PaperCategory = PaperCategory(name="Cryptography")
    log: PaperCategory = PaperCategory(name="Logic & verification")
    graph: PaperCategory = PaperCategory(name="Computer graphics")
    bio: PaperCategory = PaperCategory(name="Computational biology & bioinformatics")
    csed: PaperCategory = PaperCategory(name="Computer science education")
    ecom: PaperCategory = PaperCategory(name="Economics & computation")
    chi: PaperCategory = PaperCategory(name="Human-computer interaction")
    robotics: PaperCategory = PaperCategory(name="Robotics")
    visualization: PaperCategory = PaperCategory(name="Visualization")

class University(BaseModel):
    name: str
    rankings: Rankings
    advisors: list[Advisor] = []

class DataModel(BaseModel):
    universities: list[University] = []
    