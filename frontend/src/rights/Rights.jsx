import React from "react";
import rightsCategories from "./rightsData";

function Rights() {
  return (
    <div className="rights-page">

      {/* Header */}
      <section className="rights-header">
        <h1>Know Your Rights</h1>

        <p>
          Understand your legal rights in simple and easy-to-understand language.
        </p>
      </section>

      {/* Categories */}
      <section className="rights-categories">

        <h2>Explore Your Rights</h2>

        <div className="rights-grid">

          {rightsCategories.map((category) => (
            <div
              className="rights-card"
              key={category.id}
            >

              <div className="rights-icon">
                {category.icon}
              </div>

              <h3>{category.title}</h3>

              <p>{category.description}</p>

              <button>
                Explore
              </button>

            </div>
          ))}

        </div>

      </section>

    </div>
  );
}

export default Rights;