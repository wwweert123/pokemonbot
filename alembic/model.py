from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import INTEGER

Base = declarative_base()
metadata = Base.metadata

class CaughtPokemon(Base):

    __tablename__ = 'caught_pokemon'

    id = Column(INTEGER(11), primary_key=True, autoincrement=True)
    user_id = Column(INTEGER(11), nullable=False)
    pokemon_name = Column(String(50), nullable=False)
    caught_at = Column(TIMESTAMP, nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    def __repr__(self):
        return f"<CaughtPokemon(user_id={self.user_id}, pokemon_name='{self.pokemon_name}', caught_at={self.caught_at}>"