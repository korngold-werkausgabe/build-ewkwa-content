<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:mei="http://www.music-encoding.org/ns/mei"
  xmlns="http://www.music-encoding.org/ns/mei"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <xsl:output indent="yes"/>
  <xsl:param name="title" select="''"/>
  <xsl:param name="manifestationFile" select="''"/>

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="mei:fileDesc">
    <mei:fileDesc>
      <mei:titleStmt>
        <mei:title><xsl:value-of select="$title"/></mei:title>
      </mei:titleStmt>
    </mei:fileDesc>
    <mei:manifestationList>
      <xsl:copy-of select="document($manifestationFile)/mei:manifestation"/>
    </mei:manifestationList>
  </xsl:template>
</xsl:stylesheet>
